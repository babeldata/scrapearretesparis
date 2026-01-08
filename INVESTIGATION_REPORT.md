# Investigation Report: Paris BOVP Web Scraper Failure Analysis

**Date:** January 7, 2026
**Target URL:** https://bovp.apps.paris.fr/index.php?lvl=search_segment&id=121
**Last Successful Scrape:** December 24, 2025
**Total Records Scraped:** 5,550 arrêtés

---

## Executive Summary

The Paris BOVP (Bibliothèque en ligne de la Ville de Paris) web scraper has been failing for approximately 2 weeks since its last successful run on December 24, 2025. Based on code analysis, the scraper expects a specific HTML structure that may have changed. This report documents what the scraper expects, potential failure points, and recommendations for fixes.

---

## What the Scraper Expects to Find

### 1. HTML Structure for Search Results

The scraper is designed to parse search results from the BOVP website with the following expectations:

#### A. H3 Elements Containing "Arrêté n°"
- **Location in code:** `scraper.py`, lines 301-302
- **Logic:** `arrete_h3s = [h3 for h3 in h3_elements if h3.get_text() and 'Arrêté n°' in h3.get_text()]`
- **Expected:** Each search result should have an `<h3>` element containing the text "Arrêté n°"
- **Purpose:** Primary method to identify individual arrêté records on the page

#### B. Arrêté Number Pattern in Titles
- **Location in code:** `scraper.py`, lines 73-81
- **Regex pattern:** `r'n°\s*(\d{4}\s+[A-Z]\s+\d+)'`
- **Expected format:** "n° 2025 T 17858", "n° 2025 E 19173", etc.
- **Purpose:** Extract unique identifier for each arrêté

#### C. Document ID (explnum_id) for PDF Downloads

The scraper uses two methods to find the document ID:

**Method 1: Links within H3 element** (lines 138-146)
- Searches for `<a>` tags inside the `<h3>` element
- Looks for `onclick` attribute containing `open_visionneuse` or `sendToVisionneuse`
- **Expected pattern:** `sendToVisionneuse,(\d+)` or `sendToVisionneuse(sendToVisionneuse,\d+)`
- **Example:** `onclick="open_visionneuse(sendToVisionneuse,44443)"`

**Method 2: Parent container structure** (lines 148-186)
- If explnum_id not found in H3, traverses to parent container
- Looks for parent `<div>` with classes: `descr_notice_corps` or `notice_corps`
- Searches for links with onclick handlers in descendants

#### D. Metadata Structure

The scraper expects metadata in a specific hierarchy:

**Authority and Signatory** (lines 160-167)
- Container: Parent div with class `descr_notice_corps` or `notice_corps`
- Elements: `<span class="auteur_notCourte">`
- First span: Autorité responsable (e.g., "Direction de la Voirie et des Déplacements")
- Second span: Signataire (e.g., "Morgane SANCHEZ")

**Dates and PDF Size** (lines 169-185)
- Container: `<table class="descr_notice">`
- Rows: `<tr class="record_p_perso">`
- Structure:
  - `<td class="labelNot">`: Label (e.g., "Date de publication")
  - `<td class="labelContent">`: Value (e.g., "24/10/2025")
- Expected labels:
  - "Date de publication"
  - "Date de la signature" or "Date de signature"
  - "Poids" (PDF file size in KB)

### 2. PDF Download Mechanism

- **URL pattern:** `https://bovp.apps.paris.fr/doc_num_data.php?explnum_id={explnum_id}`
- **Method:** Direct HTTP GET request via Playwright's request API
- **Expected content-type:** `application/pdf` or `application/octet-stream`

### 3. Pagination Structure

- **Element:** `<div class="navbar">`
- **Pattern:** Regex `r'(\d+)\s*/\s*(\d+)'` to extract "current / total" results
- **Example:** "1 / 350" means 350 total results
- **Calculation:** `total_pages = (total_results // RESULTS_PER_PAGE) + 1`

---

## Potential Failure Points

### Critical Failure Scenario 1: H3 Element Changes
**Probability: HIGH**

If the website changed from `<h3>` elements to a different heading level (e.g., `<h2>`, `<h4>`) or removed headings entirely, the scraper would find 0 results.

**Symptoms:**
```python
# Line 304 would report:
logger.info(f"Page {page_num}: 0 résultats trouvés (via <h3> 'Arrêté n°')")
```

**Impact:** Complete failure - no arrêtés would be detected

### Critical Failure Scenario 2: explnum_id Pattern Changes
**Probability: MEDIUM-HIGH**

If the JavaScript function name changed (e.g., `open_visionneuse` → `openDocument`) or the parameter format changed, the scraper cannot download PDFs.

**Current patterns searched:**
- `open_visionneuse`
- `sendToVisionneuse`
- `sendToVisionneuse,(\d+)`

**Symptoms:**
```python
# Line 188-189 would report:
logger.warning(f"Pas d'explnum_id trouvé pour {numero_arrete}")
return None  # Arrêté is skipped
```

**Impact:** Arrêtés detected but PDFs not downloadable

### Critical Failure Scenario 3: Container Class Changes
**Probability: MEDIUM**

If parent container classes changed, metadata extraction would fail:
- `descr_notice_corps` → different class name
- `notice_corps` → different class name
- `auteur_notCourte` → different class name
- `descr_notice` → different class name

**Impact:** Missing metadata (dates, authority, etc.) but arrêtés still scraped

### Critical Failure Scenario 4: JavaScript-Rendered Content
**Probability: LOW-MEDIUM**

If the site migrated to a JavaScript framework (React, Vue, Angular) that renders content dynamically:
- Initial HTML might be empty
- Content loads after JavaScript execution
- Playwright's `wait_until='domcontentloaded'` might not wait long enough

**Current wait strategy:**
- `wait_until='domcontentloaded'` (line 285)
- Fixed delay of `SCRAPE_DELAY_SECONDS` (default: 2s) (line 286)

**Impact:** Empty or partial page content

### Non-Critical Failure Scenario 5: Anti-Bot Detection
**Probability: LOW**

The scraper includes anti-detection measures:
- Realistic User-Agent string (lines 360-370)
- Reasonable delays between requests
- Initial session establishment (lines 387-393)

However, if the site added:
- CAPTCHA
- Rate limiting
- IP blocking
- Advanced bot detection

**Impact:** HTTP errors, timeouts, or blocked requests

---

## Diagnostic Data from Successful Scrapes

Last successful scrape (December 24, 2025) shows the scraper was working correctly:

```csv
explnum_id: 46568, 46567, 46566, 46563, 46558
Arrêté numbers: 2025 E 19173, 2025 E 18473, 2025 C 19011, 2025 P 16797, 2025 P 16776
All metadata fields populated correctly
PDFs successfully uploaded to S3
```

This confirms:
1. H3 elements with "Arrêté n°" were found
2. explnum_id extraction was working
3. Metadata extraction was working
4. PDF downloads were successful

---

## Recommendations for Investigation

### Immediate Actions (Required)

1. **Fetch Current HTML Structure**
   ```bash
   # Install dependencies
   uv pip install playwright beautifulsoup4 lxml

   # Install browser
   playwright install firefox

   # Run test script
   python test_local.py
   ```

   This will:
   - Save HTML to `debug_local.html`
   - Show count of H3 elements with "Arrêté n°"
   - Display sendToVisionneuse patterns
   - Analyze structure around first result

2. **Compare HTML Structure**
   - Check if `<h3>` elements still exist with "Arrêté n°"
   - Verify onclick handlers still use `sendToVisionneuse`
   - Confirm parent container classes haven't changed
   - Look for new JavaScript frameworks (React, Vue indicators)

### Debug Output Analysis

The scraper automatically saves debug HTML for page 1:
- **File:** `data/debug_page_1.html` (line 294-297)
- **When:** Only for first page of each run
- Check GitHub Actions artifacts for this file from failed runs

### Fixes Based on Likely Scenarios

#### If H3 Changed to Different Element:
```python
# Current (line 301-302):
h3_elements = soup.find_all('h3')
arrete_h3s = [h3 for h3 in h3_elements if h3.get_text() and 'Arrêté n°' in h3.get_text()]

# Fix: Make element type flexible
heading_elements = soup.find_all(['h1', 'h2', 'h3', 'h4', 'div'], class_=re.compile(r'title|heading|notice'))
arrete_headings = [el for el in heading_elements if 'Arrêté n°' in el.get_text()]
```

#### If explnum_id Pattern Changed:
```python
# Current (line 142):
explnum_match = re.search(r'sendToVisionneuse,(\d+)', onclick)

# Fix: More flexible pattern
patterns = [
    r'sendToVisionneuse[^\d]*(\d+)',  # Any separator
    r'explnum_id[^\d]*(\d+)',          # Direct ID reference
    r'document[^\d]*(\d+)',             # Generic document ID
    r'data-explnum="(\d+)"',            # Data attribute
]
```

#### If Container Classes Changed:
```python
# Current (line 153-154):
classes = parent.get('class', [])
if 'descr_notice_corps' in classes or 'notice_corps' in classes:

# Fix: Regex pattern matching
if any(re.search(r'notice|description|corps', ' '.join(classes), re.I)):
```

#### If JavaScript Rendering Added:
```python
# Current (line 285):
await page.goto(url, wait_until='domcontentloaded', timeout=PAGE_LOAD_TIMEOUT)

# Fix: Wait for network idle
await page.goto(url, wait_until='networkidle', timeout=PAGE_LOAD_TIMEOUT)
# Or wait for specific element
await page.wait_for_selector('h3:has-text("Arrêté")', timeout=30000)
```

### Testing Strategy

1. **Manual Browser Test**
   - Visit https://bovp.apps.paris.fr/index.php?lvl=search_segment&id=121&page=1&nb_per_page=50
   - Inspect HTML structure with browser DevTools
   - Check if arrêtés are visible
   - Look for onclick handlers on PDF links

2. **Simplified Test Script**
   - The created `simple_fetch.py` can be used for basic HTTP testing
   - Use `test_local.py` for full Playwright testing
   - Compare output with expected patterns

3. **GitHub Actions Artifacts**
   - Check workflow runs in `.github/workflows/daily_scrape.yml`
   - Download artifacts: `scraper-logs-*.zip`, `debug-html-*.zip`
   - Review error messages in logs

---

## Technical Specifications

### Scraper Configuration
- **Browser:** Firefox (headless mode)
- **Results per page:** 50
- **Concurrent pages:** 5
- **Delays:** 2 seconds between requests
- **Timeouts:**
  - Page load: 90 seconds
  - PDF download: 60 seconds

### Dependencies
- playwright==1.41.0
- beautifulsoup4==4.12.3
- pandas==2.2.0
- boto3==1.34.34
- python-dotenv==1.0.1
- aiohttp==3.9.3
- lxml==5.1.0

### Key Files
- **Main scraper:** `/home/runner/work/scrapearretesparis/scrapearretesparis/src/scraper.py`
- **Configuration:** `/home/runner/work/scrapearretesparis/scrapearretesparis/src/config.py`
- **Test script:** `/home/runner/work/scrapearretesparis/scrapearretesparis/test_local.py`
- **Data output:** `/home/runner/work/scrapearretesparis/scrapearretesparis/data/arretes.csv`

---

## Conclusion

The scraper failure is most likely due to one of the following:

1. **Most likely:** HTML structure changes (H3 elements, onclick patterns, or class names)
2. **Possible:** Addition of JavaScript rendering requiring different wait strategies
3. **Less likely:** Anti-bot measures or major site redesign

**Next Steps:**
1. Run the test script to capture current HTML structure
2. Compare with expected patterns documented above
3. Implement fixes based on identified changes
4. Test with a small number of pages before full deployment
5. Update the scraper code to be more resilient to future changes

**Estimated Time to Fix:** 1-4 hours depending on the extent of changes

---

## Appendix: Code References

### Critical Code Sections

**H3 Detection (lines 301-302):**
```python
h3_elements = soup.find_all('h3')
arrete_h3s = [h3 for h3 in h3_elements if h3.get_text() and 'Arrêté n°' in h3.get_text()]
```

**Arrêté Number Extraction (lines 78-79):**
```python
match = re.search(r'n°\s*(\d{4}\s+[A-Z]\s+\d+)', titre)
```

**explnum_id Extraction (lines 138-146):**
```python
for link in h3_links:
    onclick = link.get('onclick', '')
    if 'open_visionneuse' in onclick or 'sendToVisionneuse' in onclick:
        explnum_match = re.search(r'sendToVisionneuse,(\d+)', onclick)
        if explnum_match:
            metadata['explnum_id'] = explnum_match.group(1)
```

**PDF Download URL (line 210):**
```python
pdf_url = f"{BASE_URL}/doc_num_data.php?explnum_id={explnum_id}"
```
