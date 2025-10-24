"""Script de test local simple pour debugger le parsing."""
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import re

async def test_parsing():
    url = "https://bovp.apps.paris.fr/index.php?lvl=search_segment&id=121&page=1&nb_per_page=50"

    async with async_playwright() as p:
        print("Lancement du navigateur...")
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print(f"Navigation vers {url}...")
        await page.goto(url, wait_until='networkidle', timeout=120000)

        content = await page.content()

        # Sauvegarder le HTML
        with open('debug_local.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print("✓ HTML sauvegardé dans debug_local.html")

        soup = BeautifulSoup(content, 'lxml')

        # Trouver les h3
        h3_elements = soup.find_all('h3')
        arrete_h3s = [h3 for h3 in h3_elements if h3.get_text() and 'Arrêté n°' in h3.get_text()]
        print(f"\n✓ Trouvé {len(arrete_h3s)} h3 avec 'Arrêté n°'")

        # Analyser le premier résultat en détail
        if arrete_h3s:
            first_h3 = arrete_h3s[0]
            titre = first_h3.get_text(strip=True)
            print(f"\n=== Premier résultat ===")
            print(f"Titre: {titre[:80]}...")

            # Extraire le numéro
            match = re.search(r'n°\s*(\d{4}\s+[A-Z]\s+\d+)', titre)
            if match:
                numero = match.group(1)
                print(f"Numéro: {numero}")

            # Analyser les 30 prochains siblings
            print("\n=== Analyse des siblings (30 prochains éléments) ===")
            current = first_h3
            for i in range(30):
                current = current.find_next_sibling()
                if not current:
                    print(f"{i+1}. [FIN - plus de siblings]")
                    break

                # Si c'est un h3, c'est le prochain résultat
                if current.name == 'h3' and 'Arrêté n°' in current.get_text():
                    print(f"{i+1}. [STOP - nouveau h3 trouvé]")
                    break

                text = current.get_text(strip=True)[:80] if hasattr(current, 'get_text') else str(current)[:80]

                # Chercher explnum_id
                explnum_info = ""
                if current.name == 'a':
                    href = current.get('href', '')
                    onclick = current.get('onclick', '')
                    if onclick:
                        explnum_info = f" | onclick={onclick[:50]}"
                    if href:
                        explnum_info += f" | href={href[:50]}"

                # Chercher dans les enfants
                if current.find('a'):
                    links = current.find_all('a')
                    for link in links:
                        onclick = link.get('onclick', '')
                        if 'sendToVisionneuse' in onclick or 'explnum' in onclick:
                            match = re.search(r'sendToVisionneuse\((\d+)\)', onclick)
                            if match:
                                explnum_info = f" | EXPLNUM_ID={match.group(1)} ✓"
                            else:
                                explnum_info = f" | onclick={onclick[:50]}"

                print(f"{i+1}. <{current.name}> {text}{explnum_info}")

        # Chercher TOUS les sendToVisionneuse dans la page
        print("\n=== Tous les sendToVisionneuse dans la page ===")
        all_links = soup.find_all('a', onclick=re.compile(r'sendToVisionneuse'))
        print(f"Trouvé {len(all_links)} liens avec sendToVisionneuse")
        for i, link in enumerate(all_links[:5]):  # Afficher les 5 premiers
            onclick = link.get('onclick', '')
            match = re.search(r'sendToVisionneuse\((\d+)\)', onclick)
            if match:
                print(f"{i+1}. explnum_id={match.group(1)} | onclick={onclick}")

        # Chercher aussi les images ou autres éléments avec explnum_id
        print("\n=== Éléments avec 'explnum' dans leurs attributs ===")
        for tag in soup.find_all(True):  # Tous les tags
            for attr, value in tag.attrs.items():
                if 'explnum' in attr.lower() or (isinstance(value, str) and 'explnum' in value.lower()):
                    print(f"<{tag.name} {attr}=\"{value}\"")
                    break

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_parsing())
