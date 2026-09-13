from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.70.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


# Sequential release metadata.
replace_once('<title>WH40k 11th V31.70</title>', '<title>WH40k 11th V31.71</title>', 'title')
replace_once('The current baseline is WH40k_11th_V31.70;', 'The current baseline is WH40k_11th_V31.71;', 'baseline')
replace_once('const APP_VERSION = "31.70";', 'const APP_VERSION = "31.71";', 'APP_VERSION')
replace_once("version: 'V31.70',", "version: 'V31.71',", 'quality version')

# Edit is rebuilt inside the approved alternate/new View surface so it inherits
# the exact same 16-column, 26px phone grid, typography, colors, spacing, and
# navigation. Canonical/legacy Edit remains untouched for one-item-at-a-time
# migration later.
frame_pattern = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
match = frame_pattern.search(text)
if not match:
    raise SystemExit('alternate View iframe not found')
np = html.unescape(match.group(2))

old_nav = "b.onclick=()=>parent.UI.selectAppMode(t);"
new_nav = "b.onclick=()=>{if(t==='edit'||(p==='edit'&&t==='view'))renderPage(t);else parent.UI.selectAppMode(t)};"
if np.count(old_nav) != 1:
    raise SystemExit(f'alternate navigation handler: expected 1 match, found {np.count(old_nav)}')
np = np.replace(old_nav, new_nav, 1)

old_edit = "if(p==='edit'){addViewHeader(f);addEditUnit(f,'edit-unit-row-first','Nazdreg','','175');addEditUnit(f,'edit-unit-row-second','Meganobz','x5','185')}"
new_edit = "if(p==='edit'){addViewHeader(f);const viewOnly=f.querySelector('.view-filter-toggle');if(viewOnly)viewOnly.remove()}"
if np.count(old_edit) != 1:
    raise SystemExit(f'alternate Edit mock: expected 1 match, found {np.count(old_edit)}')
np = np.replace(old_edit, new_edit, 1)

# Acceptance checks: the new Edit surface is intentionally only the shared
# header/navigation/grid scaffold. No Edit-unit mock or migrated Edit feature is
# rendered yet. The old addEditUnit helper may remain dormant in source so later
# migration can reuse it deliberately without affecting this blank landing page.
np_checks = [
    "if(p==='edit'){addViewHeader(f);const viewOnly=f.querySelector('.view-filter-toggle');if(viewOnly)viewOnly.remove()}",
    "if(t==='edit'||(p==='edit'&&t==='view'))renderPage(t)",
    "grid.setAttribute('aria-label',p[0].toUpperCase()+p.slice(1)+' page layout grid')",
    "addGridCells(f);addPageNavigation(f,p);",
    "grid-toggle",
    "grid-template-columns:repeat(16,var(--cell))",
    "--cell:26px",
]
missing_np = [value for value in np_checks if value not in np]
if missing_np:
    raise SystemExit('new Edit scaffold check failed: ' + ', '.join(missing_np))
if "if(p==='edit'){addViewHeader(f);addEditUnit(" in np:
    raise SystemExit('old Edit mock is still rendered in the new Edit branch')

np_srcdoc = html.escape(np, quote=True)
text = text[:match.start(2)] + np_srcdoc + text[match.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.71
    Scope: Start the Edit migration with a new blank Edit landing surface inside the approved alternate/new View layout. EDIT from the new View now stays in that embedded phone-first surface and renders the same 16-column 26px grid, shared roster header, navigation, typography, colors, spacing, and Grid toggle, with no Unit rows or migrated Edit functionality. The View-only weapon filter is omitted on the blank Edit surface. VIEW from the new Edit returns to the new View. Canonical/legacy Edit remains intact and unchanged so features can be migrated one at a time.
    Risk areas: Alternate/new View-to-Edit navigation and the new blank Edit landing scaffold only. Legacy Edit, canonical View, Cards, roster data, persistence, Waha routing, Weapons, combat behavior, and CSV data remain unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.70\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.66\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

checks = [
    '<title>WH40k 11th V31.71</title>',
    'const APP_VERSION = "31.71";',
    "version: 'V31.71',",
    'CHANGE NOTE - WH40k_11th_V31.71',
    "if(t===&#x27;edit&#x27;||(p===&#x27;edit&#x27;&amp;&amp;t===&#x27;view&#x27;))renderPage(t)",
    "if(p===&#x27;edit&#x27;){addViewHeader(f);const viewOnly=f.querySelector(&#x27;.view-filter-toggle&#x27;);if(viewOnly)viewOnly.remove()}",
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('acceptance check failed: ' + ', '.join(missing))

out.write_text(text, encoding='utf-8')
print('Built V31.71: blank new Edit landing page on the alternate View grid')
