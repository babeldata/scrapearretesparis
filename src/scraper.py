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
    validate_config
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

    async def _parse_arrete_from_element(self, element_html: str) -> Optional[Dict]:
        """Parse les métadonnées d'un arrêté depuis son HTML."""
        try:
            soup = BeautifulSoup(element_html, 'lxml')

            # Extraire le titre
            titre_elem = soup.find('div', class_='list_result_title')
            if not titre_elem:
                return None
            titre = titre_elem.get_text(strip=True)

            # Extraire le numéro d'arrêté
            numero_arrete = self._extract_numero_arrete(titre)
            if not numero_arrete:
                logger.warning(f"Impossible d'extraire le numéro d'arrêté de: {titre[:100]}")
                return None

            # Vérifier si on a déjà cet arrêté
            if numero_arrete in self.existing_arretes:
                logger.debug(f"Arrêté {numero_arrete} déjà présent, ignoré")
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
                'explnum_id': '',
                'pdf_s3_url': '',
                'date_scrape': datetime.now().isoformat()
            }

            # Chercher les métadonnées dans les divs
            for div in soup.find_all('div'):
                text = div.get_text(strip=True)

                if 'Autorité responsable :' in text:
                    metadata['autorite_responsable'] = text.replace('Autorité responsable :', '').strip()
                elif 'Signataire :' in text:
                    metadata['signataire'] = text.replace('Signataire :', '').strip()
                elif 'Date de publication :' in text:
                    metadata['date_publication'] = text.replace('Date de publication :', '').strip()
                elif 'Date de signature :' in text:
                    metadata['date_signature'] = text.replace('Date de signature :', '').strip()
                elif 'Poids :' in text and 'Ko' in text:
                    poids_match = re.search(r'(\d+)\s*Ko', text)
                    if poids_match:
                        metadata['poids_pdf_ko'] = poids_match.group(1)

            # Extraire l'explnum_id depuis le bouton "Document numérique"
            doc_link = soup.find('a', href=re.compile(r'sendToVisionneuse'))
            if doc_link:
                onclick = doc_link.get('onclick', '')
                explnum_match = re.search(r'sendToVisionneuse\((\d+)\)', onclick)
                if explnum_match:
                    metadata['explnum_id'] = explnum_match.group(1)

            if not metadata['explnum_id']:
                logger.warning(f"Pas d'explnum_id trouvé pour {numero_arrete}")
                return None

            return metadata

        except Exception as e:
            logger.error(f"Erreur lors du parsing d'un arrêté: {e}")
            return None

    async def _download_pdf(self, page: Page, explnum_id: str) -> Optional[bytes]:
        """
        Télécharge le PDF en utilisant Playwright.

        Cette fonction navigue vers la page de visionneuse et tente de récupérer le PDF.
        """
        try:
            # URL de la visionneuse
            viewer_url = f"{BASE_URL}/visionneuse.php?mode=segment&explnum_id={explnum_id}"

            logger.debug(f"Navigation vers {viewer_url}")

            # Attendre le téléchargement du PDF
            async with page.expect_download(timeout=PDF_DOWNLOAD_TIMEOUT) as download_info:
                await page.goto(viewer_url, wait_until='networkidle', timeout=PDF_DOWNLOAD_TIMEOUT)

                # Chercher un lien de téléchargement ou un iframe contenant le PDF
                # Option 1: Chercher un bouton/lien de téléchargement
                download_link = await page.query_selector('a[href*=".pdf"], a[download]')
                if download_link:
                    await download_link.click()

                # Option 2: Chercher un iframe avec un PDF
                iframe = await page.query_selector('iframe[src*=".pdf"]')
                if iframe:
                    pdf_url = await iframe.get_attribute('src')
                    if pdf_url:
                        if not pdf_url.startswith('http'):
                            pdf_url = BASE_URL + '/' + pdf_url.lstrip('/')

                        # Télécharger directement via une nouvelle page
                        response = await page.request.get(pdf_url)
                        if response.ok:
                            return await response.body()

            download = await download_info.value
            return await download.path().read_bytes()

        except PlaywrightTimeout:
            # Si pas de téléchargement automatique, essayer une approche différente
            try:
                # Chercher toutes les requêtes réseau pour des PDFs
                await page.goto(viewer_url, wait_until='networkidle', timeout=PDF_DOWNLOAD_TIMEOUT)
                await asyncio.sleep(2)  # Attendre que la page charge complètement

                # Essayer de trouver le PDF dans le contenu de la page
                content = await page.content()
                soup = BeautifulSoup(content, 'lxml')

                # Chercher des liens vers des PDFs
                pdf_links = soup.find_all('a', href=re.compile(r'\.pdf|doc_num|explnum'))
                for link in pdf_links:
                    href = link.get('href')
                    if href:
                        if not href.startswith('http'):
                            href = BASE_URL + '/' + href.lstrip('/')

                        logger.debug(f"Tentative de téléchargement depuis {href}")
                        response = await page.request.get(href)
                        if response.ok and 'application/pdf' in response.headers.get('content-type', ''):
                            return await response.body()

                logger.warning(f"Aucun PDF trouvé pour explnum_id={explnum_id}")
                return None

            except Exception as e:
                logger.error(f"Erreur lors du téléchargement du PDF {explnum_id}: {e}")
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

            await page.goto(url, wait_until='networkidle', timeout=PAGE_LOAD_TIMEOUT)
            await asyncio.sleep(SCRAPE_DELAY_SECONDS)

            # Parser le HTML
            content = await page.content()
            soup = BeautifulSoup(content, 'lxml')

            # Trouver tous les résultats
            results = soup.find_all('div', class_='list_result_line')
            logger.info(f"Page {page_num}: {len(results)} résultats trouvés")

            arretes_metadata = []
            for result in results:
                metadata = await self._parse_arrete_from_element(str(result))
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

            async with async_playwright() as p:
                # Lancer le navigateur
                logger.info("Lancement du navigateur...")
                self.browser = await p.chromium.launch(headless=True)
                context = await self.browser.new_context()

                # Créer une première page pour déterminer le nombre total de pages
                page = await context.new_page()
                await page.goto(await self._get_search_page_url(1), wait_until='networkidle', timeout=PAGE_LOAD_TIMEOUT)
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

                # Scraper toutes les pages pour récupérer les métadonnées
                all_arretes_metadata = []
                for page_num in range(1, total_pages + 1):
                    page_metadata = await self._scrape_page(page, page_num)
                    all_arretes_metadata.extend(page_metadata)

                    # Si aucun nouvel arrêté sur cette page, on peut arrêter
                    # (car les résultats sont triés par date décroissante)
                    if not page_metadata:
                        logger.info(f"Aucun nouvel arrêté sur la page {page_num}, arrêt du scraping")
                        break

                logger.info(f"Total de nouveaux arrêtés à traiter: {len(all_arretes_metadata)}")

                if not all_arretes_metadata:
                    logger.info("Aucun nouvel arrêté à traiter")
                    return

                # Traiter les arrêtés (téléchargement PDF + upload S3)
                # On crée plusieurs pages en parallèle pour aller plus vite
                semaphore = asyncio.Semaphore(MAX_CONCURRENT_PAGES)

                async def process_with_semaphore(metadata):
                    async with semaphore:
                        page = await context.new_page()
                        try:
                            await self._process_arrete(page, metadata)
                        finally:
                            await page.close()
                        await asyncio.sleep(SCRAPE_DELAY_SECONDS)

                tasks = [process_with_semaphore(m) for m in all_arretes_metadata]
                await asyncio.gather(*tasks)

                # Sauvegarder les nouveaux arrêtés dans le CSV
                await self._save_to_csv()

                logger.info(f"=== Scraping terminé: {len(self.new_arretes)} nouveaux arrêtés ajoutés ===")

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
