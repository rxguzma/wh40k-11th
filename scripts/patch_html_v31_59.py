from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.58.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def r(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


r('<title>WH40k 11th V31.58</title>', '<title>WH40k 11th V31.59</title>', 'title')
r('The current baseline is WH40k_11th_V31.58;', 'The current baseline is WH40k_11th_V31.59;', 'baseline')
r('const APP_VERSION = "31.58";', 'const APP_VERSION = "31.59";', 'APP_VERSION')
r("version: 'V31.58',", "version: 'V31.59',", 'quality version')

frame_pattern = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
match = frame_pattern.search(text)
if not match:
    raise SystemExit('alternate View iframe not found')
np = html.unescape(match.group(2))

# Weapon selection only mutes the inactive Weapon fonts. The selected Weapon keeps
# its normal colors, and when no Weapon is selected every Weapon uses normal colors.
old_css = ".weapon-row.weapon-muted .weapon-name,.weapon-row.weapon-muted .weapon-stat{color:rgba(241,243,244,.5)}\n.weapon-row.weapon-active .weapon-name,.weapon-row.weapon-active .weapon-stat{color:#80d6a3}\n.weapon-tags.weapon-muted .weapon-tag{color:var(--muted)}"
new_css = ".weapon-row.weapon-muted .weapon-name,.weapon-row.weapon-muted .weapon-stat{color:rgba(241,243,244,.5)}\n.weapon-tags.weapon-muted .weapon-tag{color:var(--muted)}"
if np.count(old_css) != 1:
    raise SystemExit(f'Weapon active CSS: expected 1 match, found {np.count(old_css)}')
np = np.replace(old_css, new_css, 1)

old_reset = "if(weaponRow){weaponRow.style.display='none';weaponRow.classList.remove('weapon-muted','weapon-active')}"
new_reset = "if(weaponRow){weaponRow.style.display='none';weaponRow.classList.remove('weapon-muted')}"
if np.count(old_reset) != 1:
    raise SystemExit(f'Weapon class reset: expected 1 match, found {np.count(old_reset)}')
np = np.replace(old_reset, new_reset, 1)

old_select = "const active=hasSelection&&i===selectedWeaponIndex;\n      const muted=hasSelection&&!active;\n      weaponRow.classList.toggle('weapon-active',active);\n      weaponRow.classList.toggle('weapon-muted',muted);"
new_select = "const muted=hasSelection&&i!==selectedWeaponIndex;\n      weaponRow.classList.toggle('weapon-muted',muted);"
if np.count(old_select) != 1:
    raise SystemExit(f'Weapon selected state: expected 1 match, found {np.count(old_select)}')
np = np.replace(old_select, new_select, 1)

for required in [
    ".weapon-row.weapon-muted .weapon-name,.weapon-row.weapon-muted .weapon-stat{color:rgba(241,243,244,.5)}",
    ".weapon-tags.weapon-muted .weapon-tag{color:var(--muted)}",
    "weaponRow.classList.remove('weapon-muted')",
    "const muted=hasSelection&&i!==selectedWeaponIndex;",
    "weaponRow.classList.toggle('weapon-muted',muted);",
]:
    if required not in np:
        raise SystemExit('alternate View check failed: ' + required)
if '.weapon-row.weapon-active' in np or "classList.toggle('weapon-active'" in np:
    raise SystemExit('selected Weapon active-green styling still present')

np_srcdoc = html.escape(np, quote=True)
text = text[:match.start(2)] + np_srcdoc + text[match.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.59
    Scope: Correct alternate View Weapon selection styling. Selecting a Weapon now changes only the font colors of the other, inactive Weapons to the muted treatment. The selected Weapon keeps its normal name/stat colors. When no Weapon is selected, all Weapon fonts use their normal colors. Existing inactive Weapon Tag muted treatment, selection ordering, filtering, compact expansion, and live data wiring are unchanged.
    Risk areas: Alternate View Weapon selected/inactive font styling only. Unit styling, Waha, View/Edit/Cards navigation, roster persistence, and combat behavior are unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.58\n'
if mark not in text:
    raise SystemExit('release note marker missing')
text = text.replace(mark, note + mark, 1)
text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.54\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

checks = [
    '<title>WH40k 11th V31.59</title>',
    'const APP_VERSION = "31.59";',
    "version: 'V31.59',",
    'rgba(241,243,244,.5)',
    "const muted=hasSelection&&i!==selectedWeaponIndex;",
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))

out.write_text(text, encoding='utf-8')
print('Built V31.59 with normal selected Weapon colors and muted inactive Weapon fonts')
