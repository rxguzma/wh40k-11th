from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.51.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def r(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


r('<title>WH40k 11th V31.51</title>', '<title>WH40k 11th V31.52</title>', 'title')
r('The current baseline is WH40k_11th_V31.51;', 'The current baseline is WH40k_11th_V31.52;', 'baseline')
r('const APP_VERSION = "31.51";', 'const APP_VERSION = "31.52";', 'APP_VERSION')
r("version: 'V31.51',", "version: 'V31.52',", 'quality version')

frame_pattern = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
match = frame_pattern.search(text)
if not match:
    raise SystemExit('alternate View iframe not found')
np = html.unescape(match.group(2))

# Insert one literal drafting-grid row immediately below row 10.
# Rows 1-10 stay fixed; every positioned item on row 11 or lower moves down one.
def shift_row_match(m):
    row = int(m.group(1))
    return f'grid-row:{row + 1}' if row >= 11 else m.group(0)

np, shifted = re.subn(r'grid-row:(\d+)', shift_row_match, np)
if shifted == 0:
    raise SystemExit('row insertion shifted no positioned items')

# Grow the drafting grid by the same one row.
old_grid_loop = 'for(let r=1;r<=39;r++)'
new_grid_loop = 'for(let r=1;r<=40;r++)'
if np.count(old_grid_loop) != 1:
    raise SystemExit(f'grid loop: expected 1 match, found {np.count(old_grid_loop)}')
np = np.replace(old_grid_loop, new_grid_loop, 1)

# The Weapon stat header was at I:P on old row 25. The row insertion moves it
# to row 26; place that existing I:P header content into the new row 11.
old_header = '.weapon-header{grid-row:26;'
new_header = '.weapon-header{grid-row:11;'
if np.count(old_header) != 1:
    raise SystemExit(f'weapon header after insertion: expected 1 match, found {np.count(old_header)}')
np = np.replace(old_header, new_header, 1)

checks_np = [
    'for(let r=1;r<=40;r++)',
    '.view-unit-row-first{grid-row:7}',
    '.detail-waha{grid-column:1/span 3;grid-row:8',
    '.detail-deep-strike{grid-column:4/span 3;grid-row:8',
    '.weapon-row-1{grid-row:9}.weapon-tags-1{grid-row:10}',
    '.weapon-header{grid-row:11;',
    '.weapon-row-2{grid-row:12}.weapon-tags-2{grid-row:13}',
    '.weapon-row-5{grid-row:18}.weapon-tags-5{grid-row:19}',
    '.view-unit-row-second{grid-row:20}',
]
missing_np = [value for value in checks_np if value not in np]
if missing_np:
    raise SystemExit('alternate View checks failed: ' + ', '.join(missing_np))

np_srcdoc = html.escape(np, quote=True)
text = text[:match.start(2)] + np_srcdoc + text[match.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.52
    Scope: Insert one literal alternate-View grid row immediately below row 10. Rows 1-10 remain fixed and all previously positioned content from row 11 downward shifts down one row. Move the existing Weapon stat header content occupying columns I:P into the newly inserted row 11, preserving its existing styling and column geometry.
    Risk areas: Alternate View grid row numbering and Weapon stat header placement only. Live Nazdreg data wiring, Waha, filters, toggles, canonical View/Edit/Cards, roster persistence, and combat behavior are unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.51\n'
if mark not in text:
    raise SystemExit('release note marker missing')
text = text.replace(mark, note + mark, 1)
text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.47\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

checks = [
    '<title>WH40k 11th V31.52</title>',
    'const APP_VERSION = "31.52";',
    "version: 'V31.52',",
    'for(let r=1;r&lt;=40;r++)',
    '.weapon-header{grid-row:11;',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))

out.write_text(text, encoding='utf-8')
print('Built V31.52 with inserted row 11 and Weapon stat header moved to I11:P11')
