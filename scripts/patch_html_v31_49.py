from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.48.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def r(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


r('<title>WH40k 11th V31.48</title>', '<title>WH40k 11th V31.49</title>', 'title')
r('The current baseline is WH40k_11th_V31.48;', 'The current baseline is WH40k_11th_V31.49;', 'baseline')
r('const APP_VERSION = "31.48";', 'const APP_VERSION = "31.49";', 'APP_VERSION')
r("version: 'V31.48',", "version: 'V31.49',", 'quality version')

frame_pattern = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
match = frame_pattern.search(text)
if not match:
    raise SystemExit('alternate View iframe not found')
np = html.unescape(match.group(2))

# Keep rows 10-12 closed by default. When Nazdreg is active, only its name
# switches to the existing success-green font color used by Main.
style_add = '''\n.view-unit-row-first.unit-active .view-unit-name{color:#80d6a3}\n.detail-deep-strike,.weapon-row-1,.weapon-tags-1{display:none}\n'''
if style_add.strip() in np:
    raise SystemExit('toggle styles already present')
if '</style>' not in np:
    raise SystemExit('style close marker missing')
np = np.replace('</style>', style_add + '</style>', 1)

# Add local open/closed state for Nazdreg and rows 10-12 only.
toggle_helper = '''\nlet nazdregOpen=false;\nfunction syncNazdregDetailVisibility(){\n  const row=grid.querySelector('.view-unit-row-first');\n  if(row)row.classList.toggle('unit-active',nazdregOpen);\n  const deep=grid.querySelector('.detail-deep-strike');\n  if(deep)deep.style.display=nazdregOpen?'flex':'none';\n  const weaponRow=grid.querySelector('.weapon-row-1');\n  if(weaponRow)weaponRow.style.display=nazdregOpen&&weaponRow.dataset.liveAvailable==='true'?'grid':'none';\n  const tagRow=grid.querySelector('.weapon-tags-1');\n  if(tagRow)tagRow.style.display=nazdregOpen&&tagRow.dataset.liveAvailable==='true'?'grid':'none';\n}\nfunction toggleNazdregDetails(){\n  nazdregOpen=!nazdregOpen;\n  syncNazdregDetailVisibility();\n}\n'''
marker = 'function refreshNazdregFromParent(){'
if np.count(marker) != 1:
    raise SystemExit(f'Nazdreg refresh marker: expected 1 match, found {np.count(marker)}')
np = np.replace(marker, toggle_helper + marker, 1)

old_missing = "  if(!data){row.style.display='none';return false}"
new_missing = "  if(!data){nazdregOpen=false;row.style.display='none';syncNazdregDetailVisibility();return false}"
if np.count(old_missing) != 1:
    raise SystemExit(f'Nazdreg missing-data branch: expected 1 match, found {np.count(old_missing)}')
np = np.replace(old_missing, new_missing, 1)

old_weapon_display = "    weaponRow.style.display=weapon?'grid':'none';"
new_weapon_display = "    weaponRow.dataset.liveAvailable=weapon?'true':'false';"
if np.count(old_weapon_display) != 1:
    raise SystemExit(f'weapon visibility assignment: expected 1 match, found {np.count(old_weapon_display)}')
np = np.replace(old_weapon_display, new_weapon_display, 1)

old_tag_display = "    tagRow.style.display=tags.length?'grid':'none';"
new_tag_display = "    tagRow.dataset.liveAvailable=tags.length?'true':'false';"
if np.count(old_tag_display) != 1:
    raise SystemExit(f'tag visibility assignment: expected 1 match, found {np.count(old_tag_display)}')
np = np.replace(old_tag_display, new_tag_display, 1)

old_refresh_end = '''  }\n  return true;\n}\nwindow.refreshNazdregFromParent=refreshNazdregFromParent;'''
new_refresh_end = '''  }\n  if(row.dataset.toggleBound!=='true'){row.dataset.toggleBound='true';row.onclick=toggleNazdregDetails}\n  nazdregOpen=false;\n  syncNazdregDetailVisibility();\n  return true;\n}\nwindow.refreshNazdregFromParent=refreshNazdregFromParent;'''
if np.count(old_refresh_end) != 1:
    raise SystemExit(f'Nazdreg refresh end: expected 1 match, found {np.count(old_refresh_end)}')
np = np.replace(old_refresh_end, new_refresh_end, 1)

np_srcdoc = html.escape(np, quote=True)
text = text[:match.start(2)] + np_srcdoc + text[match.end(2):]

note = '''  <!--\n    CHANGE NOTE - WH40k_11th_V31.49\n    Scope: Add open/closed interaction to the live Nazdreg row in alternate View. Nazdreg starts closed with rows 10-12 hidden. Tapping the Nazdreg unit row toggles it open, changes the Nazdreg unit-name font to the existing success green, and displays row 10 Deep Strike plus live row 11 Weapon and row 12 Weapon Tags when available. Tapping again returns the unit name to normal and hides rows 10-12. Reopening alternate View resets Nazdreg to closed.\n    Risk areas: Alternate View Nazdreg row and rows 10-12 only. Canonical View/Edit/Cards, roster persistence, weapon data, and all other alternate-View rows are unchanged.\n  -->\n\n'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.48\n'
if mark not in text:
    raise SystemExit('release note marker missing')
text = text.replace(mark, note + mark, 1)
text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.44\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

checks = [
    '<title>WH40k 11th V31.49</title>',
    'const APP_VERSION = "31.49";',
    "version: 'V31.49',",
    'view-unit-row-first.unit-active .view-unit-name{color:#80d6a3}',
    'detail-deep-strike,.weapon-row-1,.weapon-tags-1{display:none}',
    'function toggleNazdregDetails()',
    "row.onclick=toggleNazdregDetails",
    "weaponRow.dataset.liveAvailable=weapon?'true':'false'",
    "tagRow.dataset.liveAvailable=tags.length?'true':'false'",
    'nazdregOpen=false;',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))

out.write_text(text, encoding='utf-8')
print('Built V31.49 with Nazdreg rows 10-12 toggle')
