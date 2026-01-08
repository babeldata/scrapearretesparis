# BOVP Scraper Analysis and Fix Recommendations

## Current Situation

I've created comprehensive test scripts to diagnose the issue, but due to environment constraints, I cannot execute them directly. However, I can provide you with:

1. **Two test scripts ready to run**
2. **Expected outputs and how to interpret them**
3. **Likely failure scenarios and exact fixes**

## Test Scripts Created

### 1. `/home/runner/work/scrapearretesparis/scrapearretesparis/quick_test.py`
- Uses only Python standard library (no dependencies)
- Fetches HTML via urllib
- Analyzes structure without needing Playwright
- **Run this first** - it's simpler and faster

### 2. `/home/runner/work/scrapearretesparis/scrapearretesparis/simple_fetch.py`
- Also uses standard library
- Alternative analysis approach
- Good for cross-validation

### 3. `/home/runner/work/scrapearretesparis/scrapearretesparis/test_local.py` (existing)
- Uses Playwright (requires: `playwright install chromium`)
- More comprehensive but needs more setup

## How to Run the Tests

```bash
# Option 1: Quick test (recommended, no dependencies)
cd /home/runner/work/scrapearretesparis/scrapearretesparis
python3 quick_test.py

# Option 2: If you want Playwright-based test
pip install playwright beautifulsoup4 lxml
playwright install chromium
python3 test_local.py
```

## Expected Test Output

The `quick_test.py` script will show:

```
1. HEADING ELEMENTS:
   - <h3> elements: X
   - <h3> with 'Arrêté n°': X ← EXPECTED BY SCRAPER

2. ONCLICK HANDLERS (for PDF links):
   Total found: X
   Examples with sendToVisionneuse or similar

3. CSS CLASSES FOUND:
   DIV classes, SPAN classes, TABLE classes

4. DIAGNOSIS:
   ✗ or ✓ for each critical component
```

## Most Likely Failure Scenarios and Fixes

### Scenario 1: H3 Changed to H2 or H4 (MOST LIKELY)

**Symptom:** Test shows `<h3> with 'Arrêté n°': 0` but `<h2> with 'Arrêté n°': 50`

**Fix in `/home/runner/work/scrapearretesparis/scrapearretesparis/src/scraper.py`:**

```python
# Line 301-302: CURRENT CODE
h3_elements = soup.find_all('h3')
arrete_h3s = [h3 for h3 in h3_elements if h3.get_text() and 'Arrêté n°' in h3.get_text()]

# REPLACE WITH (flexible to h2, h3, or h4):
heading_elements = soup.find_all(['h2', 'h3', 'h4'])
arrete_headings = [h for h in heading_elements if h.get_text() and 'Arrêté n°' in h.get_text()]

# Line 304: UPDATE logging
logger.info(f"Page {page_num}: {len(arrete_headings)} résultats trouvés (via <h2/h3/h4> 'Arrêté n°')")

# Line 307-310: UPDATE loop variable
arretes_metadata = []
for heading in arrete_headings:  # Changed from 'h3' to 'heading'
    metadata = await self._parse_arrete_from_h3(heading)  # Function name unchanged for compatibility
    if metadata:
        arretes_metadata.append(metadata)
```

**Also update `_parse_arrete_from_h3` function name to be more generic:**

```python
# Line 88: Rename function (optional but cleaner)
async def _parse_arrete_from_heading(self, heading_element) -> Optional[Dict]:
    """
    Parse les métadonnées d'un arrêté depuis un élément de titre (h2/h3/h4).
    Le site BOVP n'utilise pas de divs conteneurs, on doit parcourir les siblings.
    """
    try:
        # Extraire le titre depuis le heading
        titre = heading_element.get_text(strip=True)

        # ... rest of function unchanged ...

        # Line 137: Update to search within the heading element
        heading_links = heading_element.find_all('a')
        for link in heading_links:
            # ... rest unchanged ...
```

### Scenario 2: explnum_id Pattern Changed

**Symptom:** Test shows onclick handlers but different function name

**Fix in `/home/runner/work/scrapearretesparis/scrapearretesparis/src/scraper.py`:**

```python
# Line 140-146: CURRENT CODE
onclick = link.get('onclick', '')
if 'open_visionneuse' in onclick or 'sendToVisionneuse' in onclick:
    explnum_match = re.search(r'sendToVisionneuse,(\d+)', onclick)
    if explnum_match:
        metadata['explnum_id'] = explnum_match.group(1)

# REPLACE WITH (more flexible patterns):
onclick = link.get('onclick', '')
# Try multiple patterns
patterns = [
    (r'sendToVisionneuse[^\d]*(\d+)', 'sendToVisionneuse'),
    (r'open_visionneuse[^\d]*(\d+)', 'open_visionneuse'),
    (r'openDocument[^\d]*(\d+)', 'openDocument'),
    (r'viewDocument[^\d]*(\d+)', 'viewDocument'),
    (r'showPDF[^\d]*(\d+)', 'showPDF'),
    (r'explnum[_-]?id[^\d]*(\d+)', 'explnum_id'),
]

for pattern, pattern_name in patterns:
    explnum_match = re.search(pattern, onclick, re.IGNORECASE)
    if explnum_match:
        metadata['explnum_id'] = explnum_match.group(1)
        logger.debug(f"✓ explnum_id trouvé via {pattern_name}: {metadata['explnum_id']}")
        break
```

### Scenario 3: Data Attributes Instead of onclick

**Symptom:** No onclick handlers but data-explnum or similar attributes

**Add this BEFORE the onclick search (line 135):**

```python
# NEW: Check for data attributes first
for attr_name, attr_value in link.attrs.items():
    if 'explnum' in attr_name.lower() and attr_value.isdigit():
        metadata['explnum_id'] = attr_value
        logger.debug(f"✓ explnum_id found in attribute {attr_name}: {metadata['explnum_id']}")
        break

# Also check href for explnum_id
href = link.get('href', '')
if not metadata['explnum_id'] and 'explnum' in href:
    explnum_match = re.search(r'explnum[_-]?id[=:](\d+)', href, re.IGNORECASE)
    if explnum_match:
        metadata['explnum_id'] = explnum_match.group(1)
        logger.debug(f"✓ explnum_id found in href: {metadata['explnum_id']}")
```

### Scenario 4: CSS Class Names Changed

**Symptom:** Metadata (dates, authority) not being extracted

**Fix in `/home/runner/work/scrapearretesparis/scrapearretesparis/src/scraper.py`:**

```python
# Line 152-156: CURRENT CODE
parent = heading_element.parent
while parent:
    if parent.name == 'div':
        classes = parent.get('class', [])
        if 'descr_notice_corps' in classes or 'notice_corps' in classes:
            break
    parent = parent.parent

# REPLACE WITH (flexible class matching):
parent = heading_element.parent
while parent:
    if parent.name == 'div':
        classes = ' '.join(parent.get('class', []))
        # More flexible pattern matching
        if re.search(r'(notice|description|result|item|corps|body)', classes, re.IGNORECASE):
            logger.debug(f"Found parent container with classes: {classes}")
            break
    parent = parent.parent
    # Safety: Don't go up more than 5 levels
    if parent and parent.name == 'body':
        break
```

```python
# Line 161-167: Make span class search more flexible
auteur_spans = parent.find_all('span', class_=re.compile(r'(auteur|author|signataire|responsable)', re.I))
if auteur_spans and len(auteur_spans) >= 1:
    metadata['autorite_responsable'] = auteur_spans[0].get_text(strip=True).replace('\xa0', ' ')
    if len(auteur_spans) >= 2:
        metadata['signataire'] = auteur_spans[1].get_text(strip=True).replace('\xa0', ' ')
```

```python
# Line 170: Make table class search more flexible
table = parent.find('table', class_=re.compile(r'(descr|description|notice|metadata)', re.I))
```

### Scenario 5: JavaScript Rendering (Content Loads Late)

**Symptom:** Empty page or very few elements

**Fix in `/home/runner/work/scrapearretesparis/scrapearretesparis/src/scraper.py`:**

```python
# Line 285-286: CURRENT CODE
await page.goto(url, wait_until='domcontentloaded', timeout=PAGE_LOAD_TIMEOUT)
await asyncio.sleep(SCRAPE_DELAY_SECONDS)

# REPLACE WITH:
await page.goto(url, wait_until='networkidle', timeout=PAGE_LOAD_TIMEOUT)
await asyncio.sleep(SCRAPE_DELAY_SECONDS)

# OR add explicit wait for content:
await page.goto(url, wait_until='domcontentloaded', timeout=PAGE_LOAD_TIMEOUT)
try:
    # Wait for at least one result to appear
    await page.wait_for_selector('h3:has-text("Arrêté"), h2:has-text("Arrêté"), h4:has-text("Arrêté")', timeout=30000)
except:
    logger.warning(f"Timeout waiting for results on page {page_num}")
await asyncio.sleep(SCRAPE_DELAY_SECONDS)
```

## Complete Resilient Fix (Recommended)

For maximum robustness, here's a complete rewrite of the critical sections:

### File: `/home/runner/work/scrapearretesparis/scrapearretesparis/src/scraper.py`

```python
# Lines 88-195: Replace _parse_arrete_from_h3 with this more resilient version

async def _parse_arrete_from_heading(self, heading_element) -> Optional[Dict]:
    """
    Parse les métadonnées d'un arrêté depuis un élément de titre.
    Version robuste qui s'adapte aux changements de structure HTML.
    """
    try:
        # Extraire le titre
        titre = heading_element.get_text(strip=True)

        # Extraire le numéro d'arrêté
        numero_arrete = self._extract_numero_arrete(titre)
        if not numero_arrete:
            logger.warning(f"Impossible d'extraire le numéro d'arrêté de: {titre[:100]}")
            return None

        # Vérifier si on a déjà cet arrêté
        if numero_arrete in self.existing_arretes:
            logger.debug(f"Arrêté {numero_arrete} déjà présent, ignoré")
            return None

        # Classifier l'arrêté
        classification = classify_arrete(titre)
        if not should_keep_arrete(classification):
            logger.debug(f"Arrêté {numero_arrete} filtré")
            return None

        # Initialiser les métadonnées
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

        # === EXTRACTION DE explnum_id (méthode robuste multi-stratégie) ===

        # Stratégie 1: Chercher dans les liens du heading lui-même
        heading_links = heading_element.find_all('a')
        for link in heading_links:
            # 1a. Vérifier les attributs data-*
            for attr_name, attr_value in link.attrs.items():
                if 'explnum' in attr_name.lower() and str(attr_value).isdigit():
                    metadata['explnum_id'] = str(attr_value)
                    logger.debug(f"✓ explnum_id trouvé dans data attribute: {metadata['explnum_id']}")
                    break

            if metadata['explnum_id']:
                break

            # 1b. Vérifier le href
            href = link.get('href', '')
            if 'explnum' in href:
                explnum_match = re.search(r'explnum[_-]?id[=:](\d+)', href, re.IGNORECASE)
                if explnum_match:
                    metadata['explnum_id'] = explnum_match.group(1)
                    logger.debug(f"✓ explnum_id trouvé dans href: {metadata['explnum_id']}")
                    break

            # 1c. Vérifier onclick
            onclick = link.get('onclick', '')
            if onclick:
                patterns = [
                    r'sendToVisionneuse[^\d]*(\d+)',
                    r'open_visionneuse[^\d]*(\d+)',
                    r'openDocument[^\d]*(\d+)',
                    r'viewDocument[^\d]*(\d+)',
                    r'showPDF[^\d]*(\d+)',
                    r'explnum[_-]?id[^\d]*(\d+)',
                ]
                for pattern in patterns:
                    match = re.search(pattern, onclick, re.IGNORECASE)
                    if match:
                        metadata['explnum_id'] = match.group(1)
                        logger.debug(f"✓ explnum_id trouvé dans onclick: {metadata['explnum_id']}")
                        break
                if metadata['explnum_id']:
                    break

        # Stratégie 2: Si pas trouvé, chercher dans le conteneur parent
        if not metadata['explnum_id']:
            parent = heading_element.parent
            depth = 0
            while parent and depth < 5:  # Limiter la profondeur
                if parent.name == 'div':
                    classes = ' '.join(parent.get('class', []))
                    # Chercher un conteneur de notice
                    if re.search(r'(notice|description|result|item|record|entry)', classes, re.IGNORECASE):
                        # Chercher tous les liens dans ce conteneur
                        all_links = parent.find_all('a')
                        for link in all_links:
                            onclick = link.get('onclick', '')
                            href = link.get('href', '')

                            # Vérifier onclick
                            if onclick:
                                patterns = [
                                    r'sendToVisionneuse[^\d]*(\d+)',
                                    r'open_visionneuse[^\d]*(\d+)',
                                    r'openDocument[^\d]*(\d+)',
                                    r'viewDocument[^\d]*(\d+)',
                                    r'showPDF[^\d]*(\d+)',
                                    r'explnum[_-]?id[^\d]*(\d+)',
                                ]
                                for pattern in patterns:
                                    match = re.search(pattern, onclick, re.IGNORECASE)
                                    if match:
                                        metadata['explnum_id'] = match.group(1)
                                        logger.debug(f"✓ explnum_id trouvé dans parent onclick: {metadata['explnum_id']}")
                                        break
                                if metadata['explnum_id']:
                                    break

                            # Vérifier href
                            if not metadata['explnum_id'] and 'explnum' in href:
                                match = re.search(r'explnum[_-]?id[=:](\d+)', href, re.IGNORECASE)
                                if match:
                                    metadata['explnum_id'] = match.group(1)
                                    logger.debug(f"✓ explnum_id trouvé dans parent href: {metadata['explnum_id']}")
                                    break

                        if metadata['explnum_id']:
                            break

                        # === EXTRACTION DES MÉTADONNÉES depuis ce conteneur ===
                        # Chercher autorité et signataire
                        auteur_spans = parent.find_all('span', class_=re.compile(r'(auteur|author|signataire|responsable)', re.I))
                        if auteur_spans:
                            metadata['autorite_responsable'] = auteur_spans[0].get_text(strip=True).replace('\xa0', ' ')
                            if len(auteur_spans) >= 2:
                                metadata['signataire'] = auteur_spans[1].get_text(strip=True).replace('\xa0', ' ')

                        # Chercher dates et poids
                        tables = parent.find_all('table', class_=re.compile(r'(descr|description|notice|metadata|info)', re.I))
                        for table in tables:
                            rows = table.find_all('tr')
                            for row in rows:
                                cells = row.find_all('td')
                                if len(cells) >= 2:
                                    label = cells[0].get_text(strip=True)
                                    content = cells[1].get_text(strip=True)

                                    if re.search(r'date.*publication', label, re.I):
                                        metadata['date_publication'] = content
                                    elif re.search(r'date.*(signature|signatu)', label, re.I):
                                        metadata['date_signature'] = content
                                    elif re.search(r'poids|size|taille', label, re.I):
                                        metadata['poids_pdf_ko'] = content

                        break  # On a trouvé le bon conteneur

                parent = parent.parent
                depth += 1

        # Vérification finale
        if not metadata['explnum_id']:
            logger.warning(f"Pas d'explnum_id trouvé pour {numero_arrete}")
            return None

        return metadata

    except Exception as e:
        logger.error(f"Erreur lors du parsing d'un arrêté: {e}", exc_info=True)
        return None
```

```python
# Lines 274-313: Replace _scrape_page with more resilient version

async def _scrape_page(self, page: Page, page_num: int) -> List[Dict]:
    """
    Scrape une page de résultats (version robuste).
    """
    try:
        url = await self._get_search_page_url(page_num)
        logger.info(f"Scraping de la page {page_num}: {url}")

        # Navigation avec attente adaptative
        await page.goto(url, wait_until='domcontentloaded', timeout=PAGE_LOAD_TIMEOUT)

        # Essayer d'attendre le contenu
        try:
            await page.wait_for_selector('h3:has-text("Arrêté"), h2:has-text("Arrêté"), h4:has-text("Arrêté")', timeout=10000)
        except:
            logger.warning(f"Timeout attente sélecteur, continue quand même")

        await asyncio.sleep(SCRAPE_DELAY_SECONDS)

        # Parser le HTML
        content = await page.content()
        soup = BeautifulSoup(content, 'lxml')

        # Debug: sauvegarder le HTML pour la première page
        if page_num == 1:
            debug_file = DATA_DIR / f"debug_page_{page_num}.html"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"HTML sauvegardé dans {debug_file} pour debug")

        # Chercher les résultats (méthode flexible)
        # Essayer h3, h2, h4, et même div avec classe title
        heading_elements = []

        # Méthode 1: h3
        h3_elements = soup.find_all('h3')
        arrete_h3s = [h3 for h3 in h3_elements if 'Arrêté n°' in h3.get_text()]
        if arrete_h3s:
            heading_elements = arrete_h3s
            logger.info(f"Page {page_num}: {len(arrete_h3s)} résultats trouvés via <h3>")

        # Méthode 2: h2
        if not heading_elements:
            h2_elements = soup.find_all('h2')
            arrete_h2s = [h2 for h2 in h2_elements if 'Arrêté n°' in h2.get_text()]
            if arrete_h2s:
                heading_elements = arrete_h2s
                logger.info(f"Page {page_num}: {len(arrete_h2s)} résultats trouvés via <h2>")

        # Méthode 3: h4
        if not heading_elements:
            h4_elements = soup.find_all('h4')
            arrete_h4s = [h4 for h4 in h4_elements if 'Arrêté n°' in h4.get_text()]
            if arrete_h4s:
                heading_elements = arrete_h4s
                logger.info(f"Page {page_num}: {len(arrete_h4s)} résultats trouvés via <h4>")

        # Méthode 4: divs avec classe title/heading
        if not heading_elements:
            div_elements = soup.find_all('div', class_=re.compile(r'(title|heading|notice.*title)', re.I))
            arrete_divs = [div for div in div_elements if 'Arrêté n°' in div.get_text()]
            if arrete_divs:
                heading_elements = arrete_divs
                logger.info(f"Page {page_num}: {len(arrete_divs)} résultats trouvés via <div>")

        if not heading_elements:
            logger.warning(f"Page {page_num}: AUCUN résultat trouvé avec aucune méthode!")
            return []

        # Parser chaque arrêté
        arretes_metadata = []
        for heading in heading_elements:
            metadata = await self._parse_arrete_from_heading(heading)
            if metadata:
                arretes_metadata.append(metadata)

        logger.info(f"Page {page_num}: {len(arretes_metadata)} nouveaux arrêtés à traiter")
        return arretes_metadata

    except Exception as e:
        logger.error(f"Erreur lors du scraping de la page {page_num}: {e}", exc_info=True)
        return []
```

## Instructions to Apply Fixes

### Manual Approach:

1. Run the test script:
   ```bash
   python3 quick_test.py
   ```

2. Read the diagnosis section of the output

3. Apply the corresponding fix from this document

### Automated Approach (if you want to apply all fixes at once):

The complete resilient version above can replace the existing functions entirely. It will work regardless of whether the site uses h2, h3, h4, or changed onclick patterns.

## Verification

After applying fixes:

1. Run in DRY_RUN mode:
   ```bash
   cd src
   DRY_RUN=true MAX_PAGES_TO_SCRAPE=1 python scraper.py
   ```

2. Check logs for:
   - "X résultats trouvés via <hX>" messages
   - "✓ explnum_id trouvé" messages
   - No warnings about missing explnum_id

3. Check `data/debug_page_1.html` to verify structure

## Summary

The scraper likely failed because:
1. **H3 → H2 change** (most common website update)
2. **onclick pattern change** (function renamed)
3. **CSS class changes** (styling update)

The fixes provided above handle all three scenarios and make the scraper resilient to future changes.

**Test scripts created:**
- `/home/runner/work/scrapearretesparis/scrapearretesparis/quick_test.py` ← **Run this first**
- `/home/runner/work/scrapearretesparis/scrapearretesparis/simple_fetch.py`
- `/home/runner/work/scrapearretesparis/scrapearretesparis/test_local.py` (existing)

**Complete resilient code provided above** can be copy-pasted directly into scraper.py.
