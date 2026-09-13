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

# Deep Strike is a normal orange Unit tag whenever no Weapon is selected.
# When a Weapon is selected, Deep Strike becomes an inactive tag using the
# same gray font treatment as inactive Weapon tags. Do not reduce its opacity
# simply because the Unit is expanded.
old_keyword_css = '.unit-keyword.keyword-muted{color:rgba(241,164,88,.5)}'
new_keyword_css = '.unit-keyword.keyword-muted{color:var(--muted)}'
if np.count(old_keyword_css) != 1:
    raise SystemExit(f'Unit keyword muted CSS: expected 1 match, found {np.count(old_keyword_css)}')
np = np.replace(old_keyword_css, new_keyword_css, 1)

old_deep_sync = "if(deep){deep.style.display=nazdregOpen?'flex':'none';deep.classList.toggle('keyword-muted',nazdregOpen)}\n  syncWeaponLayout();"
new_deep_sync = "if(deep)deep.style.display=nazdregOpen?'flex':'none';\n  syncWeaponLayout();"
if np.count(old_deep_sync) != 1:
    raise SystemExit(f'Deep Strike detail sync: expected 1 match, found {np.count(old_deep_sync)}')
np = np.replace(old_deep_sync, new_deep_sync, 1)

old_selection = "const hasSelection=selectedWeaponIndex!==null&&visible.includes(selectedWeaponIndex);\n  const showWeapons=Boolean(nazdregOpen&&ordered.length);"
new_selection = "const hasSelection=selectedWeaponIndex!==null&&visible.includes(selectedWeaponIndex);\n  const deep=grid.querySelector('.detail-deep-strike');\n  if(deep)deep.classList.toggle('keyword-muted',hasSelection);\n  const showWeapons=Boolean(nazdregOpen&&ordered.length);"
if np.count(old_selection) != 1:
    raise SystemExit(f'Weapon selection state marker: expected 1 match, found {np.count(old_selection)}')
np = np.replace(old_selection, new_selection, 1)

for required in [
    '.unit-keyword.keyword-muted{color:var(--muted)}',
    "if(deep)deep.style.display=nazdregOpen?'flex':'none';",
    "if(deep)deep.classList.toggle('keyword-muted',hasSelection);",
    "const hasSelection=selectedWeaponIndex!==null&&visible.includes(selectedWeaponIndex);",
]:
    if required not in np:
        raise SystemExit('alternate View check failed: ' + required)
if "deep.classList.toggle('keyword-muted',nazdregOpen)" in np:
    raise SystemExit('Deep Strike is still muted merely because the Unit is open')
if 'rgba(241,164,88,.5)' in np:
    raise SystemExit('old half-opacity Deep Strike font rule still present')

np_srcdoc = html.escape(np, quote=True)
text = text[:match.start(2)] + np_srcdoc + text[match.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.60
    Scope: Correct Deep Strike tag styling in alternate View. Deep Strike now uses its standard orange font whenever no Weapon is selected. Selecting a Weapon changes Deep Strike to the same muted gray font used by inactive Weapon tags; clearing Weapon selection restores the standard orange font. Expanding Nazdreg alone no longer makes Deep Strike translucent or muted.
    Risk areas: Alternate View Deep Strike font state only. Weapon selection/filtering, Waha, expansion, live data, and canonical View/Edit/Cards are unchanged.
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
    'color:var(--muted)',
]:
    if required not in text:
        raise SystemExit('acceptance check failed: ' + required)

out.write_text(text, encoding='utf-8')
print('Built V31.60: Deep Strike standard by default, muted only with Weapon selection')
