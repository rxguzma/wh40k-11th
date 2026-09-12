from pathlib import Path
import re

path = Path("WH40k_11th.html")
text = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    text = text.replace(old, new, 1)


# Sequential release metadata.
replace_once('<title>WH40k 11th V31.16</title>', '<title>WH40k 11th V31.17</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.16;', 'The current baseline is WH40k_11th_V31.17;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.16";', 'const APP_VERSION = "31.17";', 'APP_VERSION')
replace_once("version: 'V31.16',", "version: 'V31.17',", 'InternalQuality version')

note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.16\n"
if note_marker not in text:
    raise SystemExit("release note insertion marker missing")
new_note = """  <!--
    CHANGE NOTE - WH40k_11th_V31.17
    Scope: Fix iPhone Waha handoff by performing the Chrome custom-scheme navigation directly from the user's Waha tap instead of mutating the anchor and relying on target=_blank. The original HTTPS URL remains in the markup and only the click action is routed to googlechromes/googlechrome.
    Risk areas: Unit Waha links only. Non-Wahapedia links and Unit row behavior are unchanged.
  -->

"""
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.12\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f"old release note removal: expected 1 match, found {removed}")

# Route Waha from the actual user click. target=_blank plus a custom scheme can be
# discarded by iOS document viewers; same-window location navigation preserves the
# user gesture that iOS uses for an external-app handoff.
old_render = '''    function renderUnitWahaLink(unit, options = {}) {
      const url = getUnitWahapediaLink(unit);
      if (!url) return "";
      const buttonClass = options.button ? " unit-waha-button" : "";
      return `<a class="unit-waha-link${buttonClass}" href="${escapeAttr(url)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">Waha</a>`;
    }
'''
new_render = '''    function toChromeWahaUrl(url) {
      const value = String(url || "");
      if (/^https:\\/\\//i.test(value)) return value.replace(/^https:\\/\\//i, "googlechromes://");
      if (/^http:\\/\\//i.test(value)) return value.replace(/^http:\\/\\//i, "googlechrome://");
      return value;
    }

    function openUnitWahaInChrome(event, url) {
      if (event) {
        event.preventDefault();
        event.stopPropagation();
      }
      const chromeUrl = toChromeWahaUrl(url);
      if (!chromeUrl) return false;
      window.location.href = chromeUrl;
      return false;
    }

    function renderUnitWahaLink(unit, options = {}) {
      const url = getUnitWahapediaLink(unit);
      if (!url) return "";
      const buttonClass = options.button ? " unit-waha-button" : "";
      return `<a class="unit-waha-link${buttonClass}" href="${escapeAttr(url)}" onclick="return openUnitWahaInChrome(event, this.href)">Waha</a>`;
    }
'''
replace_once(old_render, new_render, 'Unit Waha click routing')

# Remove V31.16's document-wide anchor mutation/window.open shim. It relied on a
# target=_blank custom-scheme navigation, which the iPhone HTML viewer can drop.
route_pattern = re.compile(
    r'\n  <script>\n    \(\(\) => \{\n      const wahaHttpsPattern = /\^https:.*?\n    \}\)\(\);\n  </script>\n(?=</body>)',
    re.S,
)
text, removed = route_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f"V31.16 routing shim removal: expected 1 match, found {removed}")

checks = [
    '<title>WH40k 11th V31.17</title>',
    'const APP_VERSION = "31.17";',
    "version: 'V31.17',",
    'CHANGE NOTE - WH40k_11th_V31.17',
    'function openUnitWahaInChrome(event, url)',
    'window.location.href = chromeUrl;',
    'onclick="return openUnitWahaInChrome(event, this.href)"',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))
if 'target="_blank" rel="noopener" onclick="event.stopPropagation()">Waha</a>' in text:
    raise SystemExit('old target=_blank Waha link still present')
if 'const wahaHttpsPattern = /^https:' in text:
    raise SystemExit('old V31.16 global Waha routing shim still present')

path.write_text(text, encoding="utf-8")
print("Patched WH40k_11th.html to V31.17 with direct Waha-to-Chrome handoff")
