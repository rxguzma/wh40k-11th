from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.53.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def r(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


r('<title>WH40k 11th V31.53</title>', '<title>WH40k 11th V31.54</title>', 'title')
r('The current baseline is WH40k_11th_V31.53;', 'The current baseline is WH40k_11th_V31.54;', 'baseline')
r('const APP_VERSION = "31.53";', 'const APP_VERSION = "31.54";', 'APP_VERSION')
r("version: 'V31.53',", "version: 'V31.54',", 'quality version')

frame_pattern = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
match = frame_pattern.search(text)
if not match:
    raise SystemExit('alternate View iframe not found')
np = html.unescape(match.group(2))

# Move the current row 11 Weapon stat header two rows higher to row 9.
# Preserve row order by pushing the current row 9 Weapon 1 and row 10 tags down
# one row each to rows 10 and 11 rather than overlapping the moved header.
old_rows = '.weapon-row-1{grid-row:9}.weapon-tags-1{grid-row:10}.weapon-row-2{grid-row:12}'
new_rows = '.weapon-row-1{grid-row:10}.weapon-tags-1{grid-row:11}.weapon-row-2{grid-row:12}'
if np.count(old_rows) != 1:
    raise SystemExit(f'weapon row ordering: expected 1 match, found {np.count(old_rows)}')
np = np.replace(old_rows, new_rows, 1)

old_header = '.weapon-header{grid-row:11;'
new_header = '.weapon-header{grid-row:9;'
if np.count(old_header) != 1:
    raise SystemExit(f'weapon header row: expected 1 match, found {np.count(old_header)}')
np = np.replace(old_header, new_header, 1)

np_checks = [
    '.weapon-header{grid-row:9;',
    '.weapon-row-1{grid-row:10}.weapon-tags-1{grid-row:11}.weapon-row-2{grid-row:12}',
    '.view-unit-row-second{grid-row:20}',
    'const NAZDREG_EXPANSION_ROWS=12;',
]
missing_np = [value for value in np_checks if value not in np]
if missing_np:
    raise SystemExit('alternate View checks failed: ' + ', '.join(missing_np))

np_srcdoc = html.escape(np, quote=True)
text = text[:match.start(2)] + np_srcdoc + text[match.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.54
    Scope: Move the alternate View Weapon stat header from row 11 to row 9. Preserve the expanded-row order by moving Weapon 1 from row 9 to row 10 and its tags from row 10 to row 11. All later Nazdreg rows remain in their existing positions, and the true expand/collapse behavior is unchanged.
    Risk areas: Alternate View Nazdreg expanded rows 9-11 only. Live data wiring, Waha, filters, downstream expansion, canonical View/Edit/Cards, persistence, and combat behavior are unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.53\n'
if mark not in text:
    raise SystemExit('release note marker missing')
text = text.replace(mark, note + mark, 1)
text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.49\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

checks = [
    '<title>WH40k 11th V31.54</title>',
    'const APP_VERSION = "31.54";',
    "version: 'V31.54',",
    '.weapon-header{grid-row:9;',
    '.weapon-row-1{grid-row:10}.weapon-tags-1{grid-row:11}.weapon-row-2{grid-row:12}',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))

out.write_text(text, encoding='utf-8')
print('Built V31.54 with Weapon stat header moved from row 11 to row 9')
