from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.59.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')

replacements = [
    ('<title>WH40k 11th V31.59</title>', '<title>WH40k 11th V31.60</title>'),
    ('The current baseline is WH40k_11th_V31.59;', 'The current baseline is WH40k_11th_V31.60;'),
    ('const APP_VERSION = "31.59";', 'const APP_VERSION = "31.60";'),
    ("version: 'V31.59',", "version: 'V31.60',"),
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

# Deep Strike is standard until a Weapon is selected. While a Weapon is selected,
# the Deep Strike font becomes Main muted gray and the whole Deep Strike element
# is rendered at 50% opacity.
old_keyword_css = '.unit-keyword.keyword-muted{color:rgba(241,164,88,.5)}'
new_keyword_css = '.unit-keyword.keyword-muted{color:var(--muted);opacity:.5}'
if np.count(old_keyword_css) != 1:
    raise SystemExit(f'Unit keyword muted CSS: expected 1 match, found {np.count(old_keyword_css)}')
np = np.replace(old_keyword_css, new_keyword_css, 1)

# Inactive Weapon name/stat fonts are 50% opacity. The active Weapon name/stat
# fonts use Main's existing active green. Inactive Weapon Tag fonts remain gray.
old_weapon_css = '.weapon-row.weapon-muted .weapon-name,.weapon-row.weapon-muted .weapon-stat{color:rgba(241,243,244,.5)}\n.weapon-tags.weapon-muted .weapon-tag{color:var(--muted)}'
new_weapon_css = '.weapon-row.weapon-muted .weapon-name,.weapon-row.weapon-muted .weapon-stat{opacity:.5}\n.weapon-row.weapon-active .weapon-name,.weapon-row.weapon-active .weapon-stat{color:#80d6a3;opacity:1}\n.weapon-tags.weapon-muted .weapon-tag{color:var(--muted)}'
if np.count(old_weapon_css) != 1:
    raise SystemExit(f'Weapon muted CSS: expected 1 match, found {np.count(old_weapon_css)}')
np = np.replace(old_weapon_css, new_weapon_css, 1)

# Expanding the Unit alone must not mute Deep Strike.
old_deep_sync = "if(deep){deep.style.display=nazdregOpen?'flex':'none';deep.classList.toggle('keyword-muted',nazdregOpen)}\n  syncWeaponLayout();"
new_deep_sync = "if(deep)deep.style.display=nazdregOpen?'flex':'none';\n  syncWeaponLayout();"
if np.count(old_deep_sync) != 1:
    raise SystemExit(f'Deep Strike detail sync: expected 1 match, found {np.count(old_deep_sync)}')
np = np.replace(old_deep_sync, new_deep_sync, 1)

# Deep Strike follows Weapon selection state immediately.
old_selection = "const hasSelection=selectedWeaponIndex!==null&&visible.includes(selectedWeaponIndex);\n  const showWeapons=Boolean(nazdregOpen&&ordered.length);"
new_selection = "const hasSelection=selectedWeaponIndex!==null&&visible.includes(selectedWeaponIndex);\n  const deep=grid.querySelector('.detail-deep-strike');\n  if(deep)deep.classList.toggle('keyword-muted',hasSelection);\n  const showWeapons=Boolean(nazdregOpen&&ordered.length);"
if np.count(old_selection) != 1:
    raise SystemExit(f'Weapon selection state marker: expected 1 match, found {np.count(old_selection)}')
np = np.replace(old_selection, new_selection, 1)

# V31.59 kept the weapon-active JS state even though it removed the active-green
# CSS rule. Restore only the visual rule and keep the current selection logic.
for required in [
    "const active=hasSelection&&i===selectedWeaponIndex;",
    "weaponRow.classList.toggle('weapon-active',active);",
    "weaponRow.classList.toggle('weapon-muted',muted);",
    "tagRow.classList.toggle('weapon-muted',muted);",
    '.unit-keyword.keyword-muted{color:var(--muted);opacity:.5}',
    '.weapon-row.weapon-muted .weapon-name,.weapon-row.weapon-muted .weapon-stat{opacity:.5}',
    '.weapon-row.weapon-active .weapon-name,.weapon-row.weapon-active .weapon-stat{color:#80d6a3;opacity:1}',
    "if(deep)deep.classList.toggle('keyword-muted',hasSelection);",
]:
    if required not in np:
        raise SystemExit('alternate View check failed: ' + required)

np_srcdoc = html.escape(np, quote=True)
text = text[:match.start(2)] + np_srcdoc + text[match.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.60
    Scope: Correct alternate View selection styling. Deep Strike is standard while no Weapon is selected. When a Weapon is selected, Deep Strike uses Main muted gray text and its element is 50% opacity; clearing selection restores normal styling. Inactive Weapon name/stat fonts are 50% opacity. The selected Weapon name/stat fonts use Main active green #80d6a3. Inactive Weapon Tag fonts remain Main muted gray. Filtering, row-10 promotion, compact expansion, Waha, and live data are unchanged.
    Risk areas: Alternate View Weapon-selection and Deep Strike presentation only.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.59\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

text = re.sub(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.55\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)

for required in [
    '<title>WH40k 11th V31.60</title>',
    'const APP_VERSION = "31.60";',
    "version: 'V31.60',",
    'CHANGE NOTE - WH40k_11th_V31.60',
    'color:var(--muted);opacity:.5',
    'color:#80d6a3;opacity:1',
]:
    if required not in text:
        raise SystemExit('acceptance check failed: ' + required)

out.write_text(text, encoding='utf-8')
print('Built V31.60: normal Deep Strike until selection, 50% inactive Weapons, active-green selected Weapon')
