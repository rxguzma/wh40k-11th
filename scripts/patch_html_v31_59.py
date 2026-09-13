from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.58.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')

replacements = [
    ('<title>WH40k 11th V31.58</title>', '<title>WH40k 11th V31.59</title>'),
    ('The current baseline is WH40k_11th_V31.58;', 'The current baseline is WH40k_11th_V31.59;'),
    ('const APP_VERSION = "31.58";', 'const APP_VERSION = "31.59";'),
    ("version: 'V31.58',", "version: 'V31.59',"),
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

# Keep the existing selection logic. Inactive Weapons are already muted only while
# another Weapon is selected. Remove only the V31.58 active-green override so the
# selected Weapon stays in its normal colors and no-selection stays fully normal.
np, removed = re.subn(
    r'\.weapon-row\.weapon-active \.weapon-name,\.weapon-row\.weapon-active \.weapon-stat\{color:#80d6a3\}\n?',
    '',
    np,
    count=1,
)
if removed != 1:
    raise SystemExit(f'active Weapon color rule: expected 1 match, found {removed}')
if '.weapon-row.weapon-active .weapon-name' in np:
    raise SystemExit('active Weapon color override still present')
if '.weapon-row.weapon-muted .weapon-name,.weapon-row.weapon-muted .weapon-stat{color:rgba(241,243,244,.5)}' not in np:
    raise SystemExit('inactive Weapon muted font rule missing')

np_srcdoc = html.escape(np, quote=True)
text = text[:match.start(2)] + np_srcdoc + text[match.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.59
    Scope: Correct alternate View Weapon font behavior. When a Weapon is selected, only the inactive Weapon fonts use the existing muted treatment. The selected Weapon keeps its normal colors. When no Weapon is selected, all Weapon fonts use their normal colors. No selection logic, ordering, filtering, compact expansion, or live data wiring changed.
    Risk areas: Alternate View Weapon font color only.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.58\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

# Keep rolling history trim tolerant.
text = re.sub(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.54\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)

for required in [
    '<title>WH40k 11th V31.59</title>',
    'const APP_VERSION = "31.59";',
    "version: 'V31.59',",
    'CHANGE NOTE - WH40k_11th_V31.59',
]:
    if required not in text:
        raise SystemExit('acceptance check failed: ' + required)

out.write_text(text, encoding='utf-8')
print('Built V31.59: selected Weapon normal, inactive Weapon fonts muted, no-selection normal')
