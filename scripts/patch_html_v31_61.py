from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.60.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')

replacements = [
    ('<title>WH40k 11th V31.60</title>', '<title>WH40k 11th V31.61</title>'),
    ('The current baseline is WH40k_11th_V31.60;', 'The current baseline is WH40k_11th_V31.61;'),
    ('const APP_VERSION = "31.60";', 'const APP_VERSION = "31.61";'),
    ("version: 'V31.60',", "version: 'V31.61',"),
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

# Selection changes font treatment only. Boxes/backgrounds/borders stay unchanged.
weapon_muted_rule = '.weapon-row.weapon-muted .weapon-name,.weapon-row.weapon-muted .weapon-stat{color:rgba(241,243,244,.5)}'
if weapon_muted_rule not in np:
    raise SystemExit('inactive Weapon 50% font rule missing')
np = np.replace(
    weapon_muted_rule,
    '.weapon-row.weapon-muted{opacity:1}\n' + weapon_muted_rule + '\n.weapon-row.weapon-active .weapon-name,.weapon-row.weapon-active .weapon-stat{color:#80d6a3}',
    1,
)

tag_rule = '.weapon-tags.weapon-muted .weapon-tag{color:var(--muted)}'
if tag_rule not in np:
    raise SystemExit('inactive Weapon Tag rule missing')
np = np.replace(
    tag_rule,
    '.weapon-tags.weapon-muted{opacity:1}\n.weapon-tags.weapon-muted .weapon-tag{color:rgba(154,160,166,.5)}',
    1,
)

keyword_rule = '.unit-keyword.keyword-muted{color:var(--muted)}'
if keyword_rule not in np:
    raise SystemExit('inactive Unit keyword rule missing')
np = np.replace(keyword_rule, '.unit-keyword.keyword-muted{color:rgba(154,160,166,.5);opacity:1}', 1)

# Keep selected Weapon green and all other visible Weapons muted to 50%.
required_logic = [
    "const active=hasSelection&&i===selectedWeaponIndex;",
    "weaponRow.classList.toggle('weapon-active',active);",
    "weaponRow.classList.toggle('weapon-muted',muted);",
    "tagRow.classList.toggle('weapon-muted',muted);",
    "if(deep)deep.classList.toggle('keyword-muted',hasSelection);",
]
missing_logic = [value for value in required_logic if value not in np]
if missing_logic:
    raise SystemExit('selection logic missing: ' + ', '.join(missing_logic))

for required in [
    '.weapon-row.weapon-muted{opacity:1}',
    '.weapon-row.weapon-muted .weapon-name,.weapon-row.weapon-muted .weapon-stat{color:rgba(241,243,244,.5)}',
    '.weapon-row.weapon-active .weapon-name,.weapon-row.weapon-active .weapon-stat{color:#80d6a3}',
    '.weapon-tags.weapon-muted{opacity:1}',
    '.weapon-tags.weapon-muted .weapon-tag{color:rgba(154,160,166,.5)}',
    '.unit-keyword.keyword-muted{color:rgba(154,160,166,.5);opacity:1}',
]:
    if required not in np:
        raise SystemExit('alternate View check failed: ' + required)

np_srcdoc = html.escape(np, quote=True)
text = text[:match.start(2)] + np_srcdoc + text[match.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.61
    Scope: Correct alternate View selection visuals. Tag/button/box backgrounds and borders remain identical before and after Weapon selection; only their text changes. The selected Weapon name and stats use existing active green. Other visible Weapon name/stat text is 50% opacity. Other Weapon Tag text and Deep Strike text use muted gray at 50% opacity while their boxes remain unchanged. Clearing Weapon selection restores all normal colors.
    Risk areas: Alternate View selected/inactive font styling only. Layout, filtering, expansion, Waha, live data, and canonical View/Edit/Cards are unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.60\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

text = re.sub(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.56\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)

for required in [
    '<title>WH40k 11th V31.61</title>',
    'const APP_VERSION = "31.61";',
    "version: 'V31.61',",
    'CHANGE NOTE - WH40k_11th_V31.61',
    '#80d6a3',
    'rgba(241,243,244,.5)',
    'rgba(154,160,166,.5)',
]:
    if required not in text:
        raise SystemExit('acceptance check failed: ' + required)

out.write_text(text, encoding='utf-8')
print('Built V31.61: unchanged boxes, active Weapon green, inactive Weapon/tag text at 50%')
