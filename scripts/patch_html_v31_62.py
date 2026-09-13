from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.61.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')

replacements = [
    ('<title>WH40k 11th V31.61</title>', '<title>WH40k 11th V31.62</title>'),
    ('The current baseline is WH40k_11th_V31.61;', 'The current baseline is WH40k_11th_V31.62;'),
    ('const APP_VERSION = "31.61";', 'const APP_VERSION = "31.62";'),
    ("version: 'V31.61',", "version: 'V31.62',"),
]
for old, new in replacements:
    if old not in text:
        raise SystemExit('version marker missing: ' + old)
    text = text.replace(old, new, 1)

frame_pattern = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
match = frame_pattern.search(text)
if not match:
    raise SystemExit('alternate View iframe not found')
np = html.unescape(match.group(2))

# The entire Unit-detail row (Waha + Deep Strike) follows the same inactive text
# treatment whenever a Weapon is selected. Button/tag shells, backgrounds and borders
# remain exactly unchanged; only text is muted to Main gray at 50%.
row_css = "\n.detail-row-muted{color:rgba(154,160,166,.5)!important;opacity:1!important}\n"
if row_css.strip() in np:
    raise SystemExit('detail-row inactive CSS already present')
if '</style>' not in np:
    raise SystemExit('alternate View style marker missing')
np = np.replace('</style>', row_css + '</style>', 1)

old_selection = "const deep=grid.querySelector('.detail-deep-strike');\n  if(deep)deep.classList.toggle('keyword-muted',hasSelection);"
new_selection = "grid.querySelectorAll('.detail-waha,.detail-deep-strike').forEach(el=>{el.classList.remove('keyword-muted');el.classList.toggle('detail-row-muted',hasSelection)});"
if np.count(old_selection) != 1:
    raise SystemExit(f'detail-row selection state: expected 1 match, found {np.count(old_selection)}')
np = np.replace(old_selection, new_selection, 1)

# Preserve the V31.61 Weapon requirements exactly.
required = [
    '.weapon-row.weapon-muted .weapon-name,.weapon-row.weapon-muted .weapon-stat{color:rgba(241,243,244,.5)!important}',
    '.weapon-row.weapon-active .weapon-name,.weapon-row.weapon-active .weapon-stat{color:#80d6a3!important}',
    '.weapon-tags.weapon-muted .weapon-tag{color:rgba(154,160,166,.5)!important}',
    "weaponRow.classList.toggle('weapon-active',active);",
    "weaponRow.classList.toggle('weapon-muted',muted);",
    "tagRow.classList.toggle('weapon-muted',muted);",
    ".detail-row-muted{color:rgba(154,160,166,.5)!important;opacity:1!important}",
    "grid.querySelectorAll('.detail-waha,.detail-deep-strike').forEach(el=>{el.classList.remove('keyword-muted');el.classList.toggle('detail-row-muted',hasSelection)});",
]
missing = [value for value in required if value not in np]
if missing:
    raise SystemExit('alternate View check failed: ' + ', '.join(missing))

np_srcdoc = html.escape(np, quote=True)
text = text[:match.start(2)] + np_srcdoc + text[match.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.62
    Scope: Apply Weapon-selection inactive styling to the entire Nazdreg detail row, not only Deep Strike. When a Weapon is selected, both Waha and Deep Strike text use muted gray at 50% while their button/tag shells, backgrounds and borders remain unchanged. Clearing selection restores their normal text. Existing selected Weapon green name/stats and 50% inactive Weapon name/stats and Tag text remain unchanged.
    Risk areas: Alternate View detail-row and Weapon-selection text styling only. Layout, filtering, expansion, live data, links, and canonical View/Edit/Cards are unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.61\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

text = re.sub(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.57\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)

for required_text in [
    '<title>WH40k 11th V31.62</title>',
    'const APP_VERSION = "31.62";',
    "version: 'V31.62',",
    'CHANGE NOTE - WH40k_11th_V31.62',
    'detail-row-muted',
]:
    if required_text not in text:
        raise SystemExit('acceptance check failed: ' + required_text)

out.write_text(text, encoding='utf-8')
print('Built V31.62: Waha and Deep Strike share inactive row styling; Weapon states preserved')
