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
    "explnum_id",
    "pdf_s3_url",
    "date_scrape"
]

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

    if errors:
        raise ValueError(f"Configuration invalide: {', '.join(errors)}")

    return True
