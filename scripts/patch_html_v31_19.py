from pathlib import Path
import re

source = Path("versions/WH40k_11th_V31.18.html")
path = Path("WH40k_11th.html")
text = source.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    text = text.replace(old, new, 1)


# Sequential release metadata.
replace_once('<title>WH40k 11th V31.18</title>', '<title>WH40k 11th V31.19</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.18;', 'The current baseline is WH40k_11th_V31.19;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.18";', 'const APP_VERSION = "31.19";', 'APP_VERSION')
replace_once("version: 'V31.18',", "version: 'V31.19',", 'InternalQuality version')

# Replace the forced Chrome custom-scheme click handler with a normal HTTPS link.
# The custom scheme is swallowed by the iPhone local HTML viewer on a normal tap,
# while long-press Open Link succeeds because it uses the original HTTPS href.
old_render = '''    function toChromeWahaUrl(url) {
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
new_render = '''    function renderUnitWahaLink(unit, options = {}) {
      const url = getUnitWahapediaLink(unit);
      if (!url) return "";
      const buttonClass = options.button ? " unit-waha-button" : "";
      return `<a class="unit-waha-link${buttonClass}" href="${escapeAttr(url)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">Waha</a>`;
    }
'''
replace_once(old_render, new_render, 'Waha standard HTTPS link')

# Add the new detailed release note and keep only the five newest detailed notes.
note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.18\n"
if note_marker not in text:
    raise SystemExit("release note insertion marker missing")
new_note = """  <!--
    CHANGE NOTE - WH40k_11th_V31.19
    Scope: Restore Waha to a standard HTTPS link so a normal tap uses iOS link handling instead of the Chrome custom URL scheme. The link opens in a new browser context and stops Unit-row click propagation without preventing navigation.
    Risk areas: Unit Waha links only. Browser choice now follows the iPhone default browser setting instead of attempting to force Chrome.
  -->

"""
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.14\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f"old release note removal: expected 1 match, found {removed}")

checks = [
    '<title>WH40k 11th V31.19</title>',
    'const APP_VERSION = "31.19";',
    "version: 'V31.19',",
    'CHANGE NOTE - WH40k_11th_V31.19',
    'target="_blank" rel="noopener" onclick="event.stopPropagation()">Waha</a>',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))
if 'function openUnitWahaInChrome(' in text:
    raise SystemExit('forced Chrome Waha handler still present')
if 'function toChromeWahaUrl(' in text:
    raise SystemExit('Chrome custom-scheme converter still present')
if 'googlechromes://' in text or 'googlechrome://' in text:
    raise SystemExit('Chrome custom URL scheme still present')

path.write_text(text, encoding="utf-8")
print("Built WH40k_11th.html as V31.19 with standard single-tap HTTPS Waha links")
