#!/usr/bin/env python3
"""Test simple pour vérifier que Playwright fonctionne."""
import asyncio
from playwright.async_api import async_playwright

async def test_chromium():
    """Teste Chromium."""
    print("🧪 Test de Chromium...")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )
            print("✅ Chromium lancé avec succès")

            page = await browser.new_page()
            print("✅ Page créée avec succès")

            await page.goto('https://example.com')
            print(f"✅ Navigation réussie vers example.com")
            print(f"   Titre: {await page.title()}")

            await browser.close()
            print("✅ Chromium fermé proprement\n")
            return True
    except Exception as e:
        print(f"❌ Erreur avec Chromium: {e}\n")
        return False

async def test_firefox():
    """Teste Firefox."""
    print("🧪 Test de Firefox...")
    try:
        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=False)
            print("✅ Firefox lancé avec succès")

            page = await browser.new_page()
            print("✅ Page créée avec succès")

            await page.goto('https://example.com')
            print(f"✅ Navigation réussie vers example.com")
            print(f"   Titre: {await page.title()}")

            await browser.close()
            print("✅ Firefox fermé proprement\n")
            return True
    except Exception as e:
        print(f"❌ Erreur avec Firefox: {e}\n")
        return False

async def test_webkit():
    """Teste WebKit."""
    print("🧪 Test de WebKit...")
    try:
        async with async_playwright() as p:
            browser = await p.webkit.launch(headless=False)
            print("✅ WebKit lancé avec succès")

            page = await browser.new_page()
            print("✅ Page créée avec succès")

            await page.goto('https://example.com')
            print(f"✅ Navigation réussie vers example.com")
            print(f"   Titre: {await page.title()}")

            await browser.close()
            print("✅ WebKit fermé proprement\n")
            return True
    except Exception as e:
        print(f"❌ Erreur avec WebKit: {e}\n")
        return False

async def main():
    """Lance tous les tests."""
    print("=== Test des navigateurs Playwright ===\n")

    results = {
        'chromium': await test_chromium(),
        'firefox': await test_firefox(),
        'webkit': await test_webkit(),
    }

    print("=== Résumé ===")
    for browser, success in results.items():
        status = "✅" if success else "❌"
        print(f"{status} {browser}")

    working = [b for b, s in results.items() if s]
    if working:
        print(f"\n💡 Navigateurs fonctionnels: {', '.join(working)}")
        print(f"   Tu peux utiliser n'importe lequel de ceux-ci pour le scraper.")
    else:
        print("\n❌ Aucun navigateur ne fonctionne!")
        print("   Essaie de réinstaller: playwright install")

if __name__ == "__main__":
    asyncio.run(main())
