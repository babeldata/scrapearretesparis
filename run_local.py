#!/usr/bin/env python3
"""Script de test local simplifié pour vérifier le scraper."""
import asyncio
import sys
import os
from pathlib import Path

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from scraper import ArretesScraper
from config import DATA_DIR

async def main():
    """Lance le scraper en mode test local."""
    print("=== Test local du scraper ===\n")

    # Vérifier que .env existe
    env_file = Path(__file__).parent / '.env'
    if not env_file.exists():
        print("⚠️  Fichier .env non trouvé!")
        print("Copie .env.example vers .env et configure-le avec tes credentials MinIO/S3:\n")
        print("  cp .env.example .env")
        print("  nano .env  # ou vim, code, etc.\n")

        # Vérifier si DRY_RUN est activé
        if os.getenv('DRY_RUN', '').lower() not in ('true', '1', 'yes'):
            print("💡 Pour tester sans S3, active le mode DRY_RUN:")
            print("  export DRY_RUN=true")
            print("  python run_local.py\n")
            return

    # Afficher la config
    print("Configuration:")
    print(f"  - DRY_RUN: {os.getenv('DRY_RUN', 'false')}")
    print(f"  - MAX_PAGES_TO_SCRAPE: {os.getenv('MAX_PAGES_TO_SCRAPE', '0')} (0 = toutes)")
    print(f"  - S3_ENDPOINT_URL: {os.getenv('S3_ENDPOINT_URL', 'AWS S3 standard')}")
    print(f"  - PLAYWRIGHT_HEADLESS: {os.getenv('PLAYWRIGHT_HEADLESS', 'true')}")
    print(f"  - Data directory: {DATA_DIR}")
    print()

    if os.getenv('PLAYWRIGHT_HEADLESS', 'true').lower() == 'false':
        print("🔍 Mode DEBUG visuel activé - le navigateur va s'ouvrir")
        print("   Pour désactiver: unset PLAYWRIGHT_HEADLESS\n")

    # Limiter à 2 pages en test local par défaut
    if not os.getenv('MAX_PAGES_TO_SCRAPE'):
        os.environ['MAX_PAGES_TO_SCRAPE'] = '2'
        print("💡 Limitation à 2 pages pour le test (configure MAX_PAGES_TO_SCRAPE pour changer)\n")

    try:
        scraper = ArretesScraper()
        await scraper.run()

        print("\n✅ Test terminé avec succès!")
        print(f"\n📁 Vérifie les fichiers générés dans: {DATA_DIR}")
        print("   - arretes.csv : métadonnées")
        print("   - debug_page_*.html : HTML pour debug")

    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
