from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.50.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def r(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


r('<title>WH40k 11th V31.50</title>', '<title>WH40k 11th V31.51</title>', 'title')
r('The current baseline is WH40k_11th_V31.50;', 'The current baseline is WH40k_11th_V31.51;', 'baseline')
r('const APP_VERSION = "31.50";', 'const APP_VERSION = "31.51";', 'APP_VERSION')
r("version: 'V31.50',", "version: 'V31.51',", 'quality version')

frame_pattern = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
match = frame_pattern.search(text)
if not match:
    raise SystemExit('alternate View iframe not found')
np = html.unescape(match.group(2))

# Correct the I:P active treatment: 50% opacity on the fonts only, no green fill.
old_active = ".view-stat-header.unit-active,.view-unit-row-first.unit-active .view-unit-stat{background:rgba(31,91,53,.5)}"
new_active = ".view-stat-header.unit-active .view-stat-label,.view-unit-row-first.unit-active .view-unit-stat{color:rgba(241,243,244,.5)}"
if np.count(old_active) != 1:
    raise SystemExit(f'active stat treatment: expected 1 match, found {np.count(old_active)}')
np = np.replace(old_active, new_active, 1)

# Delete grid rows 5 and 6 for real: every positioned item below them moves up
# two rows, and the drafting grid loses two physical rows.
def shift_grid_row(match: re.Match) -> str:
    value = int(match.group(1))
    if value >= 7:
        value -= 2
    return f'grid-row:{value}'

np, shifted = re.subn(r'grid-row:(\d+)', shift_grid_row, np)
if shifted < 10:
    raise SystemExit(f'row deletion shifted too few placements: {shifted}')

old_grid_loop = 'function addGridCells(f){for(let r=1;r<=41;r++)'
new_grid_loop = 'function addGridCells(f){for(let r=1;r<=39;r++)'
if np.count(old_grid_loop) != 1:
    raise SystemExit(f'grid row count: expected 1 match, found {np.count(old_grid_loop)}')
np = np.replace(old_grid_loop, new_grid_loop, 1)

# Expected coordinates after physically deleting old rows 5 and 6.
np_checks = [
    '.view-stat-header{grid-column:9/span 8;grid-row:6;',
    '.view-unit-row-first{grid-row:7}',
    '.detail-waha{grid-column:1/span 3;grid-row:8',
    '.detail-deep-strike{grid-column:4/span 3;grid-row:8',
    '.weapon-row-1{grid-row:9}.weapon-tags-1{grid-row:10}',
    '.weapon-row-5{grid-row:17}.weapon-tags-5{grid-row:18}',
    '.view-unit-row-second{grid-row:19}',
    '.top-main-button{grid-column:15/span 2;grid-row:23;',
    'for(let r=1;r<=39;r++)',
    'color:rgba(241,243,244,.5)',
]
missing_np = [value for value in np_checks if value not in np]
if missing_np:
    raise SystemExit('alternate View checks failed: ' + ', '.join(missing_np))
if 'background:rgba(31,91,53,.5)' in np:
    raise SystemExit('old green active-stat background still present')

np_srcdoc = html.escape(np, quote=True)
text = text[:match.start(2)] + np_srcdoc + text[match.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.51
    Scope: Correct the alternate View interpretation of the prior layout request. The active Nazdreg treatment for the stat-label/stat-value area is now 50%-opacity text only, with no green background; the Nazdreg unit name still uses the existing active green font. Old grid rows 5 and 6 are physically deleted rather than merely cleared: every item below them moves up two rows and the grid shrinks from 41 to 39 rows. As a result, the stat header is now row 6, Nazdreg is row 7, Waha/Deep Strike are row 8, the five Weapon/Tag pairs occupy rows 9-18, and Meganobz starts on row 19.
    Risk areas: Alternate View grid coordinates and active Nazdreg stat text only. Live Waha/Weapon wiring, filter behavior, canonical View/Edit/Cards, persistence, and combat behavior are unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.50\n'
if mark not in text:
    raise SystemExit('release note marker missing')
text = text.replace(mark, note + mark, 1)
text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.46\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

checks = [
    '<title>WH40k 11th V31.51</title>',
    'const APP_VERSION = "31.51";',
    "version: 'V31.51',",
    'color:rgba(241,243,244,.5)',
    'for(let r=1;r&lt;=39;r++)',
    '.view-stat-header{grid-column:9/span 8;grid-row:6;',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))

out.write_text(text, encoding='utf-8')
print('Built V31.51 with true row deletion and 50% stat-text opacity')
