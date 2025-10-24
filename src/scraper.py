"""Scraper pour les arrêtés de la catégorie 'Voirie et déplacements' de Paris."""
import asyncio
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
import pandas as pd
from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup

from config import (
    SEARCH_URL,
    BASE_URL,
    CSV_FILE,
    CSV_COLUMNS,
    SCRAPE_DELAY_SECONDS,
    MAX_CONCURRENT_PAGES,
    MAX_PAGES_TO_SCRAPE,
    RESULTS_PER_PAGE,
    DATA_DIR,
    PAGE_LOAD_TIMEOUT,
    PDF_DOWNLOAD_TIMEOUT,
    FILTER_TYPE,
    validate_config,
    classify_arrete,
    should_keep_arrete
)
from s3_uploader import S3Uploader

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('scraper.log')
    ]
)
logger = logging.getLogger(__name__)


class ArretesScraper:
    """Scraper pour les arrêtés de Paris."""

    def __init__(self):
        """Initialise le scraper."""
        self.s3_uploader = S3Uploader()
        self.existing_arretes: Set[str] = set()
        self.new_arretes: List[Dict] = []
        self.browser: Optional[Browser] = None

        # Créer le répertoire data si nécessaire
        DATA_DIR.mkdir(exist_ok=True)

        # Charger les arrêtés existants
        self._load_existing_arretes()

    def _load_existing_arretes(self):
        """Charge les numéros d'arrêtés déjà scrapés depuis le CSV."""
        if CSV_FILE.exists():
            try:
                df = pd.read_csv(CSV_FILE)
                self.existing_arretes = set(df['numero_arrete'].dropna().astype(str))
                logger.info(f"{len(self.existing_arretes)} arrêtés déjà dans le CSV")
            except Exception as e:
                logger.warning(f"Impossible de charger le CSV existant: {e}")
                self.existing_arretes = set()
        else:
            logger.info("Aucun CSV existant, création d'un nouveau fichier")

    def _extract_numero_arrete(self, titre: str) -> Optional[str]:
        """
        Extrait le numéro d'arrêté depuis le titre.
        Ex: "Arrêté n° 2025 T 17858 modifiant..." -> "2025 T 17858"
        """
        match = re.search(r'n°\s*(\d{4}\s+[A-Z]\s+\d+)', titre)
        if match:
            return match.group(1)
        return None

    async def _get_search_page_url(self, page_num: int) -> str:
        """Construit l'URL pour une page de résultats donnée."""
        # La première page est à page=1
        return f"{SEARCH_URL}&page={page_num}&nb_per_page={RESULTS_PER_PAGE}"

    async def _parse_arrete_from_h3(self, h3_element) -> Optional[Dict]:
        """
        Parse les métadonnées d'un arrêté depuis un élément <h3>.
        Le site BOVP n'utilise pas de divs conteneurs, on doit parcourir les siblings.
        """
        try:
            # Extraire le titre depuis le <h3>
            titre = h3_element.get_text(strip=True)

            # Extraire le numéro d'arrêté
            numero_arrete = self._extract_numero_arrete(titre)
            if not numero_arrete:
                logger.warning(f"Impossible d'extraire le numéro d'arrêté de: {titre[:100]}")
                return None

            # Vérifier si on a déjà cet arrêté
            if numero_arrete in self.existing_arretes:
                logger.debug(f"Arrêté {numero_arrete} déjà présent, ignoré")
                return None

            # Classifier l'arrêté selon son titre
            classification = classify_arrete(titre)

            # Vérifier si on doit garder cet arrêté selon le filtre
            if not should_keep_arrete(classification):
                logger.debug(f"Arrêté {numero_arrete} filtré (FILTER_TYPE={FILTER_TYPE}, "
                           f"circulation={classification['concerne_circulation']}, "
                           f"stationnement={classification['concerne_stationnement']})")
                return None

            # Extraire les autres métadonnées
            metadata = {
                'numero_arrete': numero_arrete,
                'titre': titre,
                'autorite_responsable': '',
                'signataire': '',
                'date_publication': '',
                'date_signature': '',
                'poids_pdf_ko': '',
                'concerne_circulation': classification['concerne_circulation'],
                'concerne_stationnement': classification['concerne_stationnement'],
                'est_temporaire': classification['est_temporaire'],
                'explnum_id': '',
                'pdf_s3_url': '',
                'date_scrape': datetime.now().isoformat()
            }

            # D'abord chercher l'explnum_id dans le h3 lui-même
            # Pattern: open_visionneuse(sendToVisionneuse,44443)
            h3_links = h3_element.find_all('a')
            for link in h3_links:
                onclick = link.get('onclick', '')
                if 'open_visionneuse' in onclick or 'sendToVisionneuse' in onclick:
                    # Chercher le nombre après sendToVisionneuse,
                    explnum_match = re.search(r'sendToVisionneuse,(\d+)', onclick)
                    if explnum_match:
                        metadata['explnum_id'] = explnum_match.group(1)
                        logger.debug(f"✓ explnum_id trouvé dans h3: {metadata['explnum_id']}")
                        break

            # Les métadonnées ne sont pas siblings directs du h3, mais dans le conteneur parent
            # Remonter au conteneur parent (div.descr_notice_corps ou div.notice_corps)
            parent = h3_element.parent
            while parent:
                if parent.name == 'div':
                    classes = parent.get('class', [])
                    if 'descr_notice_corps' in classes or 'notice_corps' in classes:
                        break
                parent = parent.parent

            # Si on a trouvé le bon parent, chercher dans ses descendants
            if parent:
                # 1. Chercher autorité responsable et signataire dans <span class="auteur_notCourte">
                auteur_spans = parent.find_all('span', class_='auteur_notCourte')
                if auteur_spans and len(auteur_spans) >= 1:
                    # Le premier span est l'autorité responsable
                    metadata['autorite_responsable'] = auteur_spans[0].get_text(strip=True).replace('\xa0', ' ')
                    # Le second span (si présent) est le signataire
                    if len(auteur_spans) >= 2:
                        metadata['signataire'] = auteur_spans[1].get_text(strip=True).replace('\xa0', ' ')

                # 2. Chercher les dates et poids dans <table class="descr_notice">
                table = parent.find('table', class_='descr_notice')
                if table:
                    rows = table.find_all('tr', class_='record_p_perso')
                    for row in rows:
                        label = row.find('td', class_='labelNot')
                        content = row.find('td', class_='labelContent')
                        if label and content:
                            label_text = label.get_text(strip=True)
                            content_text = content.get_text(strip=True)

                            if 'Date de publication' in label_text:
                                metadata['date_publication'] = content_text
                            elif 'Date de la signature' in label_text or 'Date de signature' in label_text:
                                metadata['date_signature'] = content_text
                            elif 'Poids' in label_text:
                                metadata['poids_pdf_ko'] = content_text

            if not metadata['explnum_id']:
                logger.warning(f"Pas d'explnum_id trouvé pour {numero_arrete}")
                return None

            return metadata

        except Exception as e:
            logger.error(f"Erreur lors du parsing d'un arrêté: {e}")
            return None

    async def _download_pdf(self, page: Page, explnum_id: str) -> Optional[bytes]:
        """
        Télécharge le PDF directement depuis doc_num_data.php.

        Args:
            page: Page Playwright (utilisée pour faire la requête HTTP)
            explnum_id: ID du document numérique

        Returns:
            Contenu binaire du PDF ou None si échec
        """
        try:
            # URL directe du PDF
            pdf_url = f"{BASE_URL}/doc_num_data.php?explnum_id={explnum_id}"
            logger.debug(f"Téléchargement PDF depuis: {pdf_url}")

            # Télécharger directement via une requête HTTP
            response = await page.request.get(pdf_url, timeout=PDF_DOWNLOAD_TIMEOUT)

            if response.ok:
                content_type = response.headers.get('content-type', '')
                if 'application/pdf' in content_type or 'application/octet-stream' in content_type:
                    pdf_content = await response.body()
                    logger.debug(f"✓ PDF téléchargé: {len(pdf_content)} octets")
                    return pdf_content
                else:
                    logger.warning(f"Type de contenu inattendu pour {explnum_id}: {content_type}")
                    return None
            else:
                logger.warning(f"Échec HTTP {response.status} pour explnum_id={explnum_id}")
                return None

        except Exception as e:
            logger.error(f"Erreur lors du téléchargement du PDF {explnum_id}: {e}")
            return None

    async def _process_arrete(self, page: Page, metadata: Dict) -> bool:
        """
        Traite un arrêté : télécharge le PDF et l'upload sur S3.

        Returns:
            True si succès, False sinon
        """
        try:
            numero = metadata['numero_arrete']
            explnum_id = metadata['explnum_id']

            logger.info(f"Traitement de l'arrêté {numero} (explnum_id={explnum_id})")

            # Télécharger le PDF
            pdf_content = await self._download_pdf(page, explnum_id)
            if not pdf_content:
                logger.warning(f"Impossible de télécharger le PDF pour {numero}")
                # On garde quand même les métadonnées sans le PDF
                metadata['pdf_s3_url'] = 'ERROR: PDF non téléchargé'
                self.new_arretes.append(metadata)
                return False

            # Uploader vers S3
            s3_url = self.s3_uploader.upload_pdf(pdf_content, numero)
            if not s3_url:
                logger.warning(f"Impossible d'uploader le PDF pour {numero}")
                metadata['pdf_s3_url'] = 'ERROR: Upload S3 échoué'
                self.new_arretes.append(metadata)
                return False

            metadata['pdf_s3_url'] = s3_url
            self.new_arretes.append(metadata)
            self.existing_arretes.add(numero)

            logger.info(f"✓ Arrêté {numero} traité avec succès")
            return True

        except Exception as e:
            logger.error(f"Erreur lors du traitement de l'arrêté {metadata.get('numero_arrete', 'UNKNOWN')}: {e}")
            return False

    async def _scrape_page(self, page: Page, page_num: int) -> List[Dict]:
        """
        Scrape une page de résultats.

        Returns:
            Liste des métadonnées des arrêtés de cette page
        """
        try:
            url = await self._get_search_page_url(page_num)
            logger.info(f"Scraping de la page {page_num}: {url}")

            await page.goto(url, wait_until='domcontentloaded', timeout=PAGE_LOAD_TIMEOUT)
            await asyncio.sleep(SCRAPE_DELAY_SECONDS)

            # Parser le HTML
            content = await page.content()
            soup = BeautifulSoup(content, 'lxml')

            # Debug: sauvegarder le HTML pour analyse
            if page_num == 1:
                debug_file = DATA_DIR / f"debug_page_{page_num}.html"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"HTML sauvegardé dans {debug_file} pour debug")

            # Le site BOVP n'utilise pas de divs conteneurs avec classes CSS
            # Les résultats sont identifiés par des <h3> contenant "Arrêté n°"
            h3_elements = soup.find_all('h3')
            arrete_h3s = [h3 for h3 in h3_elements if h3.get_text() and 'Arrêté n°' in h3.get_text()]

            logger.info(f"Page {page_num}: {len(arrete_h3s)} résultats trouvés (via <h3> 'Arrêté n°')")

            arretes_metadata = []
            for h3 in arrete_h3s:
                metadata = await self._parse_arrete_from_h3(h3)
                if metadata:
                    arretes_metadata.append(metadata)

            logger.info(f"Page {page_num}: {len(arretes_metadata)} nouveaux arrêtés à traiter")
            return arretes_metadata

        except Exception as e:
            logger.error(f"Erreur lors du scraping de la page {page_num}: {e}")
            return []

    async def run(self):
        """Lance le scraper."""
        try:
            logger.info("=== Démarrage du scraper d'arrêtés ===")
            validate_config()
            logger.info(f"Filtre actif: FILTER_TYPE={FILTER_TYPE}")

            async with async_playwright() as p:
                # Lancer le navigateur
                logger.info("Lancement du navigateur...")

                # Mode headless ou non (pour debug)
                import os
                headless = os.getenv('PLAYWRIGHT_HEADLESS', 'true').lower() != 'false'
                browser_type = os.getenv('PLAYWRIGHT_BROWSER', 'chromium').lower()
                logger.info(f"Mode headless: {headless}, Navigateur: {browser_type}")

                # Sélectionner le navigateur
                if browser_type == 'firefox':
                    browser_engine = p.firefox
                    launch_kwargs = {'headless': headless}
                elif browser_type == 'webkit':
                    browser_engine = p.webkit
                    launch_kwargs = {'headless': headless}
                else:  # chromium par défaut
                    browser_engine = p.chromium
                    # Arguments du navigateur pour stabilité et anti-détection
                    launch_kwargs = {
                        'headless': headless,
                        'args': [
                            '--no-sandbox',
                            '--disable-setuid-sandbox',
                            '--disable-dev-shm-usage',
                            '--disable-blink-features=AutomationControlled',
                        ]
                    }

                self.browser = await browser_engine.launch(**launch_kwargs)

                # Configurer le contexte pour ressembler à un vrai navigateur
                context = await self.browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080},
                    locale='fr-FR',
                    timezone_id='Europe/Paris',
                    extra_http_headers={
                        'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Connection': 'keep-alive',
                    }
                )

                # Créer une première page
                page = await context.new_page()

                # Écouter les erreurs réseau pour debug (ignorer AJAX non critiques)
                def log_request_failure(request):
                    url = request.url
                    # Ignorer les erreurs AJAX normales (facettes, compteurs, etc.)
                    if 'ajax.php' in url or 'cart_info.php' in url:
                        return  # Ces requêtes AJAX sont souvent annulées, c'est normal
                    # Logger uniquement les vraies erreurs (pages, PDFs)
                    logger.warning(f"Requête échouée: {url} - {request.failure}")

                page.on('requestfailed', log_request_failure)

                # Navigation préalable vers la page d'accueil pour établir une session
                logger.info("Établissement de la session sur la page d'accueil...")
                try:
                    await page.goto(BASE_URL, wait_until='domcontentloaded', timeout=PAGE_LOAD_TIMEOUT)
                    await asyncio.sleep(2)  # Laisser le temps au site de charger complètement
                    logger.info("✓ Session établie")
                except Exception as e:
                    logger.warning(f"Impossible d'accéder à la page d'accueil: {e}")

                # Maintenant naviguer vers la page de résultats
                logger.info(f"Navigation vers la page de résultats...")
                await page.goto(await self._get_search_page_url(1), wait_until='domcontentloaded', timeout=PAGE_LOAD_TIMEOUT)
                content = await page.content()
                soup = BeautifulSoup(content, 'lxml')

                # Trouver le nombre total de résultats
                pagination_info = soup.find('div', class_='navbar')
                total_results = 0
                if pagination_info:
                    match = re.search(r'(\d+)\s*/\s*(\d+)', pagination_info.get_text())
                    if match:
                        total_results = int(match.group(2))

                total_pages = (total_results // RESULTS_PER_PAGE) + 1
                logger.info(f"Total de résultats: {total_results}, Total de pages: {total_pages}")

                if MAX_PAGES_TO_SCRAPE > 0:
                    total_pages = min(total_pages, MAX_PAGES_TO_SCRAPE)
                    logger.info(f"Limitation à {total_pages} pages")

                # Scraper et traiter page par page (sauvegarde incrémentale)
                total_arretes_traites = 0
                semaphore = asyncio.Semaphore(MAX_CONCURRENT_PAGES)

                for page_num in range(1, total_pages + 1):
                    # 1. Scraper les métadonnées de cette page
                    page_metadata = await self._scrape_page(page, page_num)

                    # Si aucun nouvel arrêté sur cette page, on peut arrêter
                    # (car les résultats sont triés par date décroissante)
                    if not page_metadata:
                        logger.info(f"Aucun nouvel arrêté sur la page {page_num}, arrêt du scraping")
                        break

                    # 2. Traiter immédiatement les PDFs de cette page
                    async def process_with_semaphore(metadata):
                        async with semaphore:
                            pdf_page = await context.new_page()
                            try:
                                await self._process_arrete(pdf_page, metadata)
                            finally:
                                await pdf_page.close()
                            await asyncio.sleep(SCRAPE_DELAY_SECONDS)

                    tasks = [process_with_semaphore(m) for m in page_metadata]
                    await asyncio.gather(*tasks)

                    # 3. Sauvegarder le CSV après chaque page (sauvegarde incrémentale)
                    if self.new_arretes:
                        await self._save_to_csv()
                        total_arretes_traites += len(page_metadata)
                        logger.info(f"💾 Progression: {total_arretes_traites} arrêtés traités, CSV sauvegardé")
                        # Réinitialiser la liste pour la prochaine page
                        self.new_arretes = []

                logger.info(f"=== Scraping terminé: {total_arretes_traites} nouveaux arrêtés ajoutés ===")

        except Exception as e:
            logger.error(f"Erreur critique dans le scraper: {e}")
            raise
        finally:
            if self.browser:
                await self.browser.close()

    async def _save_to_csv(self):
        """Sauvegarde les nouveaux arrêtés dans le CSV."""
        if not self.new_arretes:
            logger.info("Aucun nouvel arrêté à sauvegarder")
            return

        try:
            # Créer un DataFrame avec les nouveaux arrêtés
            new_df = pd.DataFrame(self.new_arretes, columns=CSV_COLUMNS)

            # Ajouter au CSV existant ou créer un nouveau
            if CSV_FILE.exists():
                new_df.to_csv(CSV_FILE, mode='a', header=False, index=False)
            else:
                new_df.to_csv(CSV_FILE, mode='w', header=True, index=False)

            logger.info(f"{len(self.new_arretes)} arrêtés sauvegardés dans {CSV_FILE}")

        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du CSV: {e}")
            raise


async def main():
    """Point d'entrée principal."""
    scraper = ArretesScraper()
    await scraper.run()


if __name__ == "__main__":
    asyncio.run(main())
