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
replace_once('<title>WH40k 11th V31.15</title>', '<title>WH40k 11th V31.16</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.15;', 'The current baseline is WH40k_11th_V31.16;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.15";', 'const APP_VERSION = "31.16";', 'APP_VERSION')
replace_once("version: 'V31.15',", "version: 'V31.16',", 'InternalQuality version')

note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.15\n"
if note_marker not in text:
    raise SystemExit("release note insertion marker missing")
new_note = """  <!--
    CHANGE NOTE - WH40k_11th_V31.16
    Scope: Route all Wahapedia links through the Chrome URL scheme so tapping Waha from the local iPhone HTML app hands the page to Chrome. Applies to normal anchors and Wahapedia URLs opened through window.open; all non-Wahapedia links are unchanged.
    Risk areas: External Wahapedia link routing only. iOS may still show its normal confirmation before handing the link to Chrome.
  -->

"""
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.11\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f"old release note removal: expected 1 match, found {removed}")

# Route Wahapedia links to Chrome while leaving every other URL untouched.
router_marker = "  <!-- V31.16 WAHA_CHROME_ROUTER -->"
if router_marker in text:
    raise SystemExit("Wahapedia Chrome router already present")
body_marker = "</body>"
if body_marker not in text:
    raise SystemExit("closing body marker missing")
router = r'''  <!-- V31.16 WAHA_CHROME_ROUTER -->
  <script>
    (() => {
      const wahaHttpsPattern = /^https:\/\/(?:www\.)?wahapedia\.ru\//i;
      const wahaHttpPattern = /^http:\/\/(?:www\.)?wahapedia\.ru\//i;

      function toChromeWahaUrl(value) {
        const url = String(value || "");
        if (wahaHttpsPattern.test(url)) return url.replace(/^https:\/\//i, "googlechromes://");
        if (wahaHttpPattern.test(url)) return url.replace(/^http:\/\//i, "googlechrome://");
        return url;
      }

      const nativeWindowOpen = typeof window.open === "function" ? window.open.bind(window) : null;
      if (nativeWindowOpen) {
        window.open = function(url, ...args) {
          const routedUrl = typeof url === "string" ? toChromeWahaUrl(url) : url;
          return nativeWindowOpen(routedUrl, ...args);
        };
      }

      document.addEventListener("click", event => {
        const target = event.target;
        const anchor = target && typeof target.closest === "function" ? target.closest("a[href]") : null;
        if (!anchor) return;
        const href = anchor.getAttribute("href") || "";
        const routedHref = toChromeWahaUrl(href);
        if (routedHref !== href) anchor.setAttribute("href", routedHref);
      }, true);
    })();
  </script>
'''
text = text.replace(body_marker, router + body_marker, 1)

checks = [
    '<title>WH40k 11th V31.16</title>',
    'const APP_VERSION = "31.16";',
    "version: 'V31.16',",
    'CHANGE NOTE - WH40k_11th_V31.16',
    'V31.16 WAHA_CHROME_ROUTER',
    'googlechromes://',
    'googlechrome://',
    'wahaHttpsPattern',
    'nativeWindowOpen'
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))

path.write_text(text, encoding="utf-8")
print("Patched WH40k_11th.html to V31.16 with Chrome routing for Wahapedia links")
