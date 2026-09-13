from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.68.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def r(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


r('<title>WH40k 11th V31.68</title>', '<title>WH40k 11th V31.69</title>', 'title')
r('The current baseline is WH40k_11th_V31.68;', 'The current baseline is WH40k_11th_V31.69;', 'baseline')
r('const APP_VERSION = "31.68";', 'const APP_VERSION = "31.69";', 'APP_VERSION')
r("version: 'V31.68',", "version: 'V31.69',", 'quality version')

# The alternate View is a srcdoc iframe. Keep its Waha link from navigating or
# opening a new target itself; instead, pass the live URL synchronously to Main.
frame_pattern = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
match = frame_pattern.search(text)
if not match:
    raise SystemExit('alternate View iframe not found')
np = html.unescape(match.group(2))

old_waha_click = "w.target='_blank';w.rel='noopener';w.onclick=e=>e.stopPropagation();"
new_waha_click = "w.onclick=e=>{e.preventDefault();e.stopPropagation();const url=String(w.getAttribute('href')||'').trim();if(!url||url==='#')return;try{if(parent&&typeof parent.openAlternateViewWaha==='function')parent.openAlternateViewWaha(url)}catch(_){}};"
if np.count(old_waha_click) != 1:
    raise SystemExit(f'iframe Waha click handler: expected 1 match, found {np.count(old_waha_click)}')
np = np.replace(old_waha_click, new_waha_click, 1)

np_srcdoc = html.escape(np, quote=True)
text = text[:match.start(2)] + np_srcdoc + text[match.end(2):]

# Open Waha from the top-level application context. This preserves the working
# top-level new-window behavior while preventing the nested srcdoc iframe from
# becoming the navigation owner.
parent_helper = '''    function openAlternateViewWaha(url) {
      const href = String(url || '').trim();
      if (!/^https?:\\/\\//i.test(href)) return false;
      try {
        window.open(href, '_blank', 'noopener');
        return true;
      } catch (_) {
        return false;
      }
    }
    window.openAlternateViewWaha = openAlternateViewWaha;

'''
parent_marker = '    function selectAppMode(mode) {'
if text.count(parent_marker) != 1:
    raise SystemExit(f'parent helper insertion point: expected 1 match, found {text.count(parent_marker)}')
if 'window.openAlternateViewWaha = openAlternateViewWaha;' in text:
    raise SystemExit('parent Waha helper already present')
text = text.replace(parent_marker, parent_helper + parent_marker, 1)

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.69
    Scope: Correct alternate-View Waha navigation regression. The Waha control inside the srcdoc iframe now prevents its own navigation and passes the existing live Waha URL to Main. Main opens that URL in a new top-level browsing target, so the nested iframe no longer owns the external navigation. No Waha URL/data, layout, styling, roster, weapon, or persistence behavior is changed.
    Risk areas: Alternate View Waha click routing only. Canonical View/Edit/Cards, CSV URLs, roster persistence, weapons, filters, combat behavior, and all other alternate-View rows are unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.68\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.64\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

checks = [
    '<title>WH40k 11th V31.69</title>',
    'const APP_VERSION = "31.69";',
    "version: 'V31.69',",
    'window.openAlternateViewWaha = openAlternateViewWaha;',
    "window.open(href, '_blank', 'noopener');",
    'typeof parent.openAlternateViewWaha===&#x27;function&#x27;',
    'e.preventDefault();e.stopPropagation();',
    'CHANGE NOTE - WH40k_11th_V31.69',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('acceptance check failed: ' + ', '.join(missing))
if 'w.target=&#x27;_blank&#x27;;w.rel=&#x27;noopener&#x27;;w.onclick=e=&gt;e.stopPropagation();' in text:
    raise SystemExit('old iframe-owned Waha target still present')

out.write_text(text, encoding='utf-8')
print('Built V31.69: Waha routed through Main instead of srcdoc iframe')
