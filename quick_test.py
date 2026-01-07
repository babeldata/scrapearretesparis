#!/usr/bin/env python3
"""Quick test script using only standard library to investigate HTML structure."""
import urllib.request
import urllib.error
import re
import sys
from html.parser import HTMLParser

class BOVPAnalyzer(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_h3 = False
        self.in_h2 = False
        self.in_h4 = False
        self.current_text = ""
        self.h3_count = 0
        self.h2_count = 0
        self.h4_count = 0
        self.arrete_h3_count = 0
        self.arrete_h2_count = 0
        self.arrete_h4_count = 0
        self.onclick_handlers = []
        self.data_attributes = []
        self.div_classes = set()
        self.span_classes = set()
        self.table_classes = set()
        self.first_arrete_context = []
        self.capture_context = 0
        self.depth = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        # Track heading elements
        if tag == 'h3':
            self.in_h3 = True
            self.h3_count += 1
            self.current_text = ""
        elif tag == 'h2':
            self.in_h2 = True
            self.h2_count += 1
            self.current_text = ""
        elif tag == 'h4':
            self.in_h4 = True
            self.h4_count += 1
            self.current_text = ""

        # Track onclick handlers
        if 'onclick' in attrs_dict:
            onclick = attrs_dict['onclick']
            if 'visionneuse' in onclick.lower() or 'explnum' in onclick.lower() or 'document' in onclick.lower():
                self.onclick_handlers.append({
                    'tag': tag,
                    'onclick': onclick,
                    'href': attrs_dict.get('href', ''),
                    'class': attrs_dict.get('class', '')
                })

        # Track data attributes with explnum or document
        for attr_name, attr_value in attrs:
            if 'explnum' in attr_name.lower() or 'doc' in attr_name.lower():
                self.data_attributes.append({
                    'tag': tag,
                    'attr': attr_name,
                    'value': attr_value
                })

        # Track CSS classes
        if 'class' in attrs_dict:
            classes = attrs_dict['class']
            if tag == 'div':
                self.div_classes.add(classes)
            elif tag == 'span':
                self.span_classes.add(classes)
            elif tag == 'table':
                self.table_classes.add(classes)

        # Capture context around first arrêté
        if self.capture_context > 0:
            attr_str = ' '.join([f'{k}="{v}"' for k, v in attrs[:3]]) if attrs else ''
            self.first_arrete_context.append(f"{'  ' * self.depth}<{tag} {attr_str}>")
            self.depth += 1
            self.capture_context -= 1

    def handle_endtag(self, tag):
        if tag == 'h3':
            self.in_h3 = False
            if 'Arrêté n°' in self.current_text or 'Arrete n°' in self.current_text:
                self.arrete_h3_count += 1
                if self.arrete_h3_count == 1:
                    self.capture_context = 50
                    self.first_arrete_context.append(f"\n=== First H3 with Arrêté: {self.current_text[:100]} ===\n")
        elif tag == 'h2':
            self.in_h2 = False
            if 'Arrêté n°' in self.current_text or 'Arrete n°' in self.current_text:
                self.arrete_h2_count += 1
        elif tag == 'h4':
            self.in_h4 = False
            if 'Arrêté n°' in self.current_text or 'Arrete n°' in self.current_text:
                self.arrete_h4_count += 1

        if self.capture_context > 0 and self.depth > 0:
            self.depth -= 1

    def handle_data(self, data):
        if self.in_h3 or self.in_h2 or self.in_h4:
            self.current_text += data
        if self.capture_context > 0:
            if data.strip():
                self.first_arrete_context.append(f"{'  ' * self.depth}[TEXT: {data.strip()[:60]}]")

def main():
    url = "https://bovp.apps.paris.fr/index.php?lvl=search_segment&id=121&page=1&nb_per_page=50"

    print("=" * 80)
    print("BOVP Website Structure Analysis")
    print("=" * 80)
    print(f"Target URL: {url}")
    print()

    try:
        # Create request with headers
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
        )

        print("Fetching HTML...")
        with urllib.request.urlopen(req, timeout=30) as response:
            # Handle gzip encoding
            import gzip
            content = response.read()
            if response.headers.get('Content-Encoding') == 'gzip':
                content = gzip.decompress(content)
            html = content.decode('utf-8', errors='ignore')

        print(f"✓ HTML fetched: {len(html)} characters")
        print()

        # Save HTML
        with open('bovp_debug.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("✓ HTML saved to: bovp_debug.html")
        print()

        # Parse HTML
        print("Parsing HTML structure...")
        parser = BOVPAnalyzer()
        parser.feed(html)

        # Results
        print("=" * 80)
        print("ANALYSIS RESULTS")
        print("=" * 80)
        print()

        print("1. HEADING ELEMENTS:")
        print(f"   - <h2> elements: {parser.h2_count}")
        print(f"   - <h2> with 'Arrêté n°': {parser.arrete_h2_count}")
        print(f"   - <h3> elements: {parser.h3_count}")
        print(f"   - <h3> with 'Arrêté n°': {parser.arrete_h3_count} ← EXPECTED BY SCRAPER")
        print(f"   - <h4> elements: {parser.h4_count}")
        print(f"   - <h4> with 'Arrêté n°': {parser.arrete_h4_count}")
        print()

        if parser.arrete_h3_count == 0:
            print("   ⚠️  WARNING: NO H3 ELEMENTS WITH 'Arrêté n°' FOUND!")
            print("   This is likely the main cause of scraper failure.")
            if parser.arrete_h2_count > 0:
                print(f"   → Found {parser.arrete_h2_count} H2 elements with 'Arrêté n°' instead")
            if parser.arrete_h4_count > 0:
                print(f"   → Found {parser.arrete_h4_count} H4 elements with 'Arrêté n°' instead")
        print()

        print("2. ONCLICK HANDLERS (for PDF links):")
        print(f"   Total found: {len(parser.onclick_handlers)}")
        if parser.onclick_handlers:
            print("   First 5 examples:")
            for i, handler in enumerate(parser.onclick_handlers[:5]):
                print(f"   {i+1}. <{handler['tag']}> onclick=\"{handler['onclick'][:80]}...\"")
                # Try to extract explnum_id
                patterns = [
                    (r'sendToVisionneuse[^\d]*(\d+)', 'sendToVisionneuse'),
                    (r'explnum_id[^\d]*(\d+)', 'explnum_id'),
                    (r'openDocument[^\d]*(\d+)', 'openDocument'),
                    (r'viewDocument[^\d]*(\d+)', 'viewDocument'),
                ]
                for pattern, name in patterns:
                    match = re.search(pattern, handler['onclick'])
                    if match:
                        print(f"      → Found {name}: ID = {match.group(1)}")
                        break
        else:
            print("   ⚠️  WARNING: NO ONCLICK HANDLERS FOUND!")
            print("   Scraper expects: onclick with 'sendToVisionneuse' or 'open_visionneuse'")
        print()

        print("3. DATA ATTRIBUTES (alternative ID storage):")
        print(f"   Total found: {len(parser.data_attributes)}")
        if parser.data_attributes:
            for i, attr in enumerate(parser.data_attributes[:5]):
                print(f"   {i+1}. <{attr['tag']}> {attr['attr']}=\"{attr['value'][:50]}\"")
        print()

        print("4. CSS CLASSES FOUND:")
        print(f"   DIV classes ({len(parser.div_classes)} unique):")
        target_div_classes = ['descr_notice_corps', 'notice_corps', 'notice', 'result', 'item']
        for cls in sorted(parser.div_classes)[:15]:
            marker = " ← EXPECTED" if any(t in cls for t in target_div_classes) else ""
            print(f"      - {cls}{marker}")
        print()

        print(f"   SPAN classes ({len(parser.span_classes)} unique):")
        target_span_classes = ['auteur_notCourte', 'author', 'signataire']
        for cls in sorted(parser.span_classes)[:15]:
            marker = " ← EXPECTED" if any(t in cls for t in target_span_classes) else ""
            print(f"      - {cls}{marker}")
        print()

        print(f"   TABLE classes ({len(parser.table_classes)} unique):")
        for cls in sorted(parser.table_classes)[:10]:
            marker = " ← EXPECTED" if 'descr_notice' in cls else ""
            print(f"      - {cls}{marker}")
        print()

        print("5. REGEX SEARCH FOR KEY PATTERNS:")
        patterns = {
            'H3 with Arrêté': r'<h3[^>]*>.*?Arrêté n°.*?</h3>',
            'H2 with Arrêté': r'<h2[^>]*>.*?Arrêté n°.*?</h2>',
            'H4 with Arrêté': r'<h4[^>]*>.*?Arrêté n°.*?</h4>',
            'sendToVisionneuse': r'sendToVisionneuse[^\d]*(\d+)',
            'open_visionneuse': r'open_visionneuse[^\d]*(\d+)',
            'explnum_id in HTML': r'explnum[_-]?id[^\d]*(\d+)',
            'data-explnum': r'data-explnum=["\'](\d+)["\']',
        }

        for name, pattern in patterns.items():
            matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
            count = len(matches)
            print(f"   - {name}: {count} found")
            if count > 0 and count < 10:
                if isinstance(matches[0], str) and matches[0].isdigit():
                    print(f"      Examples: {', '.join(matches[:3])}")
                else:
                    print(f"      First: {str(matches[0])[:80]}...")
        print()

        print("6. CONTEXT AROUND FIRST ARRÊTÉ:")
        if parser.first_arrete_context:
            print('\n'.join(parser.first_arrete_context[:30]))
        else:
            print("   No arrêté found to show context")
        print()

        print("=" * 80)
        print("DIAGNOSIS:")
        print("=" * 80)

        if parser.arrete_h3_count == 0:
            print("✗ CRITICAL: Scraper expects <h3> elements with 'Arrêté n°' but found 0")
            if parser.arrete_h2_count > 0:
                print(f"  → Website now uses <h2> elements ({parser.arrete_h2_count} found)")
                print("  → FIX: Change line 301 in scraper.py from find_all('h3') to find_all('h2')")
            elif parser.arrete_h4_count > 0:
                print(f"  → Website now uses <h4> elements ({parser.arrete_h4_count} found)")
                print("  → FIX: Change line 301 in scraper.py from find_all('h3') to find_all('h4')")
            else:
                print("  → Website may have changed to a different structure entirely")
                print("  → Investigate bovp_debug.html manually")
        else:
            print(f"✓ Found {parser.arrete_h3_count} <h3> elements with 'Arrêté n°'")

        if len(parser.onclick_handlers) == 0:
            print("✗ CRITICAL: No onclick handlers found for PDF downloads")
            print("  → Website may have changed PDF access mechanism")
            print("  → Check bovp_debug.html for alternative link patterns")
        else:
            print(f"✓ Found {len(parser.onclick_handlers)} onclick handlers")

        print("=" * 80)
        print()
        print("Next steps:")
        print("1. Review bovp_debug.html file")
        print("2. Check the diagnosis above")
        print("3. Apply suggested fixes to scraper.py")
        print()

    except urllib.error.HTTPError as e:
        print(f"✗ HTTP Error: {e.code} - {e.reason}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"✗ URL Error: {e.reason}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
