from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.57.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def r(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


r('<title>WH40k 11th V31.57</title>', '<title>WH40k 11th V31.58</title>', 'title')
r('The current baseline is WH40k_11th_V31.57;', 'The current baseline is WH40k_11th_V31.58;', 'baseline')
r('const APP_VERSION = "31.57";', 'const APP_VERSION = "31.58";', 'APP_VERSION')
r("version: 'V31.57',", "version: 'V31.58',", 'quality version')

frame_pattern = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
match = frame_pattern.search(text)
if not match:
    raise SystemExit('alternate View iframe not found')
np = html.unescape(match.group(2))

# Non-selected visible Weapons use 50% text opacity. The selected Weapon uses
# the same active-green font treatment as the active Unit name, for both Weapon
# name and Weapon stats. Tags keep the existing muted-gray behavior on other Weapons.
old_muted_css = ".weapon-row.weapon-muted .weapon-name,.weapon-row.weapon-muted .weapon-stat{color:rgba(241,243,244,.75)}\n.weapon-tags.weapon-muted .weapon-tag{color:var(--muted)}"
new_muted_css = ".weapon-row.weapon-muted .weapon-name,.weapon-row.weapon-muted .weapon-stat{color:rgba(241,243,244,.5)}\n.weapon-row.weapon-active .weapon-name,.weapon-row.weapon-active .weapon-stat{color:#80d6a3}\n.weapon-tags.weapon-muted .weapon-tag{color:var(--muted)}"
if np.count(old_muted_css) != 1:
    raise SystemExit(f'Weapon muted CSS: expected 1 match, found {np.count(old_muted_css)}')
np = np.replace(old_muted_css, new_muted_css, 1)

old_reset = "if(weaponRow){weaponRow.style.display='none';weaponRow.classList.remove('weapon-muted')}"
new_reset = "if(weaponRow){weaponRow.style.display='none';weaponRow.classList.remove('weapon-muted','weapon-active')}"
if np.count(old_reset) != 1:
    raise SystemExit(f'Weapon class reset: expected 1 match, found {np.count(old_reset)}')
np = np.replace(old_reset, new_reset, 1)

old_select = "const muted=hasSelection&&i!==selectedWeaponIndex;\n      weaponRow.classList.toggle('weapon-muted',muted);"
new_select = "const active=hasSelection&&i===selectedWeaponIndex;\n      const muted=hasSelection&&!active;\n      weaponRow.classList.toggle('weapon-active',active);\n      weaponRow.classList.toggle('weapon-muted',muted);"
if np.count(old_select) != 1:
    raise SystemExit(f'Weapon selected state: expected 1 match, found {np.count(old_select)}')
np = np.replace(old_select, new_select, 1)

for required in [
    ".weapon-row.weapon-muted .weapon-name,.weapon-row.weapon-muted .weapon-stat{color:rgba(241,243,244,.5)}",
    ".weapon-row.weapon-active .weapon-name,.weapon-row.weapon-active .weapon-stat{color:#80d6a3}",
    "weaponRow.classList.remove('weapon-muted','weapon-active')",
    "const active=hasSelection&&i===selectedWeaponIndex;",
    "weaponRow.classList.toggle('weapon-active',active);",
    "weaponRow.classList.toggle('weapon-muted',muted);",
]:
    if required not in np:
        raise SystemExit('alternate View check failed: ' + required)
if 'rgba(241,243,244,.75)' in np:
    raise SystemExit('old 75% non-active Weapon opacity still present')

np_srcdoc = html.escape(np, quote=True)
text = text[:match.start(2)] + np_srcdoc + text[match.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.58
    Scope: In alternate View, when a Weapon is selected, its Weapon name and stat values use the existing active-green font color. Other visible Weapons remain present but their Weapon name/stat text is reduced from 75% to 50% opacity. Existing gray treatment for non-selected Weapon Tag text remains unchanged. Weapon selection ordering, row-10 promotion, filtering, compact expansion, and live data wiring are unchanged.
    Risk areas: Alternate View Weapon selected/muted font styling only. Unit styling, Waha, View/Edit/Cards navigation, roster persistence, and combat behavior are unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.57\n'
if mark not in text:
    raise SystemExit('release note marker missing')
text = text.replace(mark, note + mark, 1)
text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.53\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

checks = [
    '<title>WH40k 11th V31.58</title>',
    'const APP_VERSION = "31.58";',
    "version: 'V31.58',",
    'rgba(241,243,244,.5)',
    'weapon-active',
    '#80d6a3',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))

out.write_text(text, encoding='utf-8')
print('Built V31.58 with active-green selected Weapon and 50%-opacity non-selected Weapons')
