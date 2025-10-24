"""Script de debug pour analyser le HTML du site BOVP."""
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def debug_html():
    """Récupère et analyse le HTML de la première page."""
    url = "https://bovp.apps.paris.fr/index.php?lvl=search_segment&id=121&page=1&nb_per_page=50"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print(f"Navigation vers {url}...")
        await page.goto(url, wait_until='networkidle', timeout=120000)

        # Sauvegarder le HTML
        content = await page.content()
        with open('/tmp/bovp_debug.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print("HTML sauvegardé dans /tmp/bovp_debug.html")

        # Parser avec BeautifulSoup
        soup = BeautifulSoup(content, 'lxml')

        # Chercher différentes classes possibles
        print("\n=== Recherche de classes ===")

        # Classes recherchées
        classes_to_test = [
            'list_result_line',
            'result',
            'notice',
            'record',
            'item',
            'document',
        ]

        for cls in classes_to_test:
            results = soup.find_all('div', class_=cls)
            print(f"div.{cls}: {len(results)} trouvé(s)")

            results_any = soup.find_all(class_=cls)
            print(f"*.{cls}: {len(results_any)} trouvé(s)")

        # Chercher tous les divs avec des classes
        print("\n=== Toutes les classes de divs présentes ===")
        all_divs = soup.find_all('div', class_=True)
        classes_found = set()
        for div in all_divs[:50]:  # Limiter aux 50 premiers
            if div.get('class'):
                classes_found.update(div.get('class'))

        print(f"Classes trouvées: {sorted(classes_found)}")

        # Chercher le mot "Arrêté" pour localiser les résultats
        print("\n=== Recherche du texte 'Arrêté' ===")
        arretes = soup.find_all(string=lambda text: text and 'Arrêté' in text)
        print(f"Trouvé {len(arretes)} mentions d'Arrêté")

        if arretes:
            print("\nPremiers parents des mentions 'Arrêté':")
            for i, arrete in enumerate(arretes[:3]):
                parent = arrete.parent
                print(f"\n{i+1}. Parent: {parent.name}")
                print(f"   Classes: {parent.get('class')}")
                print(f"   Texte (100 premiers caractères): {parent.get_text()[:100]}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_html())
