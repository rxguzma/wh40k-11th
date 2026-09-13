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

# Add final-state overrides only. Backgrounds, borders, button shells and tag boxes
# remain unchanged; selection affects text only.
visual_css = '''
.weapon-row.weapon-muted{opacity:1!important}
.weapon-row.weapon-muted .weapon-name,.weapon-row.weapon-muted .weapon-stat{color:rgba(241,243,244,.5)!important}
.weapon-row.weapon-active .weapon-name,.weapon-row.weapon-active .weapon-stat{color:#80d6a3!important}
.weapon-tags.weapon-muted{opacity:1!important}
.weapon-tags.weapon-muted .weapon-tag{color:rgba(154,160,166,.5)!important}
.unit-keyword.keyword-muted{color:rgba(154,160,166,.5)!important;opacity:1!important}
'''
if visual_css.strip() in np:
    raise SystemExit('V31.61 visual overrides already present')
if '</style>' not in np:
    raise SystemExit('alternate View style marker missing')
np = np.replace('</style>', visual_css + '</style>', 1)

# Selection logic must already mark the selected Weapon active, other Weapons muted,
# their tags muted, and Deep Strike muted while a Weapon is selected.
required_logic = [
    "weaponRow.classList.toggle('weapon-active',active);",
    "weaponRow.classList.toggle('weapon-muted',muted);",
    "tagRow.classList.toggle('weapon-muted',muted);",
    "if(deep)deep.classList.toggle('keyword-muted',hasSelection);",
]
missing_logic = [value for value in required_logic if value not in np]
if missing_logic:
    raise SystemExit('selection logic missing: ' + ', '.join(missing_logic))

for required in [
    '.weapon-row.weapon-muted{opacity:1!important}',
    '.weapon-row.weapon-muted .weapon-name,.weapon-row.weapon-muted .weapon-stat{color:rgba(241,243,244,.5)!important}',
    '.weapon-row.weapon-active .weapon-name,.weapon-row.weapon-active .weapon-stat{color:#80d6a3!important}',
    '.weapon-tags.weapon-muted{opacity:1!important}',
    '.weapon-tags.weapon-muted .weapon-tag{color:rgba(154,160,166,.5)!important}',
    '.unit-keyword.keyword-muted{color:rgba(154,160,166,.5)!important;opacity:1!important}',
]:
    if required not in np:
        raise SystemExit('alternate View check failed: ' + required)

np_srcdoc = html.escape(np, quote=True)
text = text[:match.start(2)] + np_srcdoc + text[match.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.61
    Scope: Correct alternate View selection visuals. Tag/button/box backgrounds and borders remain identical before and after Weapon selection; only their text changes. The selected Weapon name and stats use existing active green. Other visible Weapon name/stat text is 50% opacity. Other Weapon Tag text and Deep Strike text use muted gray at 50% opacity while their boxes remain unchanged. Clearing Weapon selection restores normal colors.
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
print('Built V31.61: boxes unchanged, active Weapon green, inactive text at 50%')
