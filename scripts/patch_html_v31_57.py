from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.56.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def r(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


r('<title>WH40k 11th V31.56</title>', '<title>WH40k 11th V31.57</title>', 'title')
r('The current baseline is WH40k_11th_V31.56;', 'The current baseline is WH40k_11th_V31.57;', 'baseline')
r('const APP_VERSION = "31.56";', 'const APP_VERSION = "31.57";', 'APP_VERSION')
r("version: 'V31.56',", "version: 'V31.57',", 'quality version')

frame_pattern = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
match = frame_pattern.search(text)
if not match:
    raise SystemExit('alternate View iframe not found')
np = html.unescape(match.group(2))

# Unit keywords that are not relevant to the current active detail state use the
# same 50%-opacity font treatment as the active M/T/SV/W/LD/OC text. Keep the
# keyword button/background itself unchanged; only the font is dimmed.
keyword_css = ".unit-keyword.keyword-muted{color:rgba(241,164,88,.5)}\n"
if keyword_css.strip() in np:
    raise SystemExit('muted unit keyword CSS already present')
if '</style>' not in np:
    raise SystemExit('alternate View style close marker missing')
np = np.replace('</style>', keyword_css + '</style>', 1)

old_deep = "const ds=document.createElement('div');ds.className='detail-deep-strike';ds.textContent='DEEP STRIKE';f.appendChild(ds);"
new_deep = "const ds=document.createElement('div');ds.className='detail-deep-strike unit-keyword';ds.textContent='DEEP STRIKE';f.appendChild(ds);"
if np.count(old_deep) != 1:
    raise SystemExit(f'Deep Strike keyword marker: expected 1 match, found {np.count(old_deep)}')
np = np.replace(old_deep, new_deep, 1)

old_sync = "const deep=grid.querySelector('.detail-deep-strike');\n  if(deep)deep.style.display=nazdregOpen?'flex':'none';\n  syncWeaponLayout();"
new_sync = "const deep=grid.querySelector('.detail-deep-strike');\n  if(deep){deep.style.display=nazdregOpen?'flex':'none';deep.classList.toggle('keyword-muted',nazdregOpen)}\n  syncWeaponLayout();"
if np.count(old_sync) != 1:
    raise SystemExit(f'Deep Strike visibility sync: expected 1 match, found {np.count(old_sync)}')
np = np.replace(old_sync, new_sync, 1)

for required in [
    '.unit-keyword.keyword-muted{color:rgba(241,164,88,.5)}',
    "ds.className='detail-deep-strike unit-keyword'",
    "deep.classList.toggle('keyword-muted',nazdregOpen)",
    '.view-stat-header.unit-active .view-stat-label,.view-unit-row-first.unit-active .view-unit-stat{color:rgba(241,243,244,.5)}',
    "function selectWeapon(index)",
]:
    if required not in np:
        raise SystemExit('alternate View check failed: ' + required)

np_srcdoc = html.escape(np, quote=True)
text = text[:match.start(2)] + np_srcdoc + text[match.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.57
    Scope: In alternate View, non-relevant Unit keyword text under the active Unit now uses the same 50%-opacity treatment as the active M/T/SV/W/LD/OC stat text. Deep Strike is marked as a Unit keyword and its orange font is rendered at 50% alpha while Nazdreg is open; the keyword button background/border, Waha link, Weapon filtering, Weapon selection, and compact expansion remain unchanged. This establishes the muted-keyword treatment for additional Unit keywords as they are wired.
    Risk areas: Alternate View Unit keyword font treatment only. Live roster/Weapon data, View/Edit/Cards navigation, persistence, and combat behavior are unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.56\n'
if mark not in text:
    raise SystemExit('release note marker missing')
text = text.replace(mark, note + mark, 1)
text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.52\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

checks = [
    '<title>WH40k 11th V31.57</title>',
    'const APP_VERSION = "31.57";',
    "version: 'V31.57',",
    '.unit-keyword.keyword-muted{color:rgba(241,164,88,.5)}',
    'detail-deep-strike unit-keyword',
    'keyword-muted',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))

out.write_text(text, encoding='utf-8')
print('Built V31.57 with 50%-opacity non-relevant Unit keyword text')
