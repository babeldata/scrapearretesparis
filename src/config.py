"""Configuration pour le scraper d'arrêtés de Paris."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Chemins
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CSV_FILE = DATA_DIR / "arretes.csv"

# URL du site
BASE_URL = "https://bovp.apps.paris.fr"
SEARCH_URL = f"{BASE_URL}/index.php?lvl=search_segment&id=121"

# Configuration S3 / MinIO
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")  # Pour MinIO, peut être n'importe quoi
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")  # Ex: https://minio.example.com ou None pour AWS

# Configuration du scraper
SCRAPE_DELAY_SECONDS = int(os.getenv("SCRAPE_DELAY_SECONDS", "2"))
MAX_CONCURRENT_PAGES = int(os.getenv("MAX_CONCURRENT_PAGES", "5"))
MAX_PAGES_TO_SCRAPE = int(os.getenv("MAX_PAGES_TO_SCRAPE", "0"))  # 0 = toutes
DRY_RUN = os.getenv("DRY_RUN", "false").lower() in ("true", "1", "yes")

# Filtrage des arrêtés
# Options: "all" (tous), "circulation" (seulement circulation), "stationnement" (seulement stationnement)
FILTER_TYPE = os.getenv("FILTER_TYPE", "all").lower()

# Timeouts Playwright (en millisecondes)
PAGE_LOAD_TIMEOUT = int(os.getenv("PAGE_LOAD_TIMEOUT", "90000"))  # 90 secondes pour charger une page
PDF_DOWNLOAD_TIMEOUT = int(os.getenv("PDF_DOWNLOAD_TIMEOUT", "60000"))  # 60 secondes pour télécharger un PDF

# Pagination
RESULTS_PER_PAGE = 50  # Compromis entre vitesse et nombre de requêtes

# Colonnes du CSV
CSV_COLUMNS = [
    "numero_arrete",
    "titre",
    "autorite_responsable",
    "signataire",
    "date_publication",
    "date_signature",
    "poids_pdf_ko",
    "concerne_circulation",      # Booléen: arrêté concerne la circulation
    "concerne_stationnement",    # Booléen: arrêté concerne le stationnement
    "est_temporaire",            # Booléen: arrêté temporaire (vs permanent)
    "explnum_id",
    "pdf_s3_url",
    "date_scrape"
]

# Fonctions de classification des arrêtés
def classify_arrete(titre: str) -> dict:
    """
    Analyse le titre d'un arrêté pour extraire ses caractéristiques.

    Args:
        titre: Titre complet de l'arrêté

    Returns:
        Dict avec clés: concerne_circulation, concerne_stationnement, est_temporaire
    """
    titre_lower = titre.lower()

    # Mots-clés pour la circulation
    mots_circulation = [
        'circulation',
        'sens unique',
        'sens interdit',
        'voie',
        'interdiction de circuler',
        'accès',
        'fermeture',
        'déviation',
        'circulation générale',
    ]

    # Mots-clés pour le stationnement
    mots_stationnement = [
        'stationnement',
        'parking',
        'zone bleue',
        'livraison',
        'règles de stationnement',
    ]

    # Mots-clés pour temporaire
    mots_temporaire = [
        'à titre provisoire',
        'provisoire',
        'temporaire',
        'provisoirement',
    ]

    # Mots-clés pour permanent (rare mais possible)
    mots_permanent = [
        'permanent',
        'définitif',
        'définitiv',
    ]

    concerne_circulation = any(mot in titre_lower for mot in mots_circulation)
    concerne_stationnement = any(mot in titre_lower for mot in mots_stationnement)

    # Temporaire si mots-clés présents, permanent sinon
    est_temporaire = any(mot in titre_lower for mot in mots_temporaire)

    return {
        'concerne_circulation': concerne_circulation,
        'concerne_stationnement': concerne_stationnement,
        'est_temporaire': est_temporaire
    }


def should_keep_arrete(classification: dict) -> bool:
    """
    Détermine si un arrêté doit être conservé selon FILTER_TYPE.

    Args:
        classification: Dict retourné par classify_arrete()

    Returns:
        True si l'arrêté doit être conservé, False sinon
    """
    if FILTER_TYPE == "all":
        return True
    elif FILTER_TYPE == "circulation":
        # Garder uniquement si concerne circulation
        return classification['concerne_circulation']
    elif FILTER_TYPE == "stationnement":
        # Garder uniquement si concerne stationnement
        return classification['concerne_stationnement']
    else:
        # Par défaut, tout garder
        return True


# Validation de la configuration
def validate_config():
    """Valide que la configuration est correcte."""
    errors = []

    # En mode DRY_RUN, S3 n'est pas nécessaire
    if not DRY_RUN:
        if not AWS_ACCESS_KEY_ID:
            errors.append("AWS_ACCESS_KEY_ID manquant")
        if not AWS_SECRET_ACCESS_KEY:
            errors.append("AWS_SECRET_ACCESS_KEY manquant")
        if not S3_BUCKET_NAME:
            errors.append("S3_BUCKET_NAME manquant")

    # Valider FILTER_TYPE
    if FILTER_TYPE not in ["all", "circulation", "stationnement"]:
        errors.append(f"FILTER_TYPE invalide: '{FILTER_TYPE}' (options: all, circulation, stationnement)")

    if errors:
        raise ValueError(f"Configuration invalide: {', '.join(errors)}")

    return True
