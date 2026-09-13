from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.55.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def r(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


r('<title>WH40k 11th V31.55</title>', '<title>WH40k 11th V31.56</title>', 'title')
r('The current baseline is WH40k_11th_V31.55;', 'The current baseline is WH40k_11th_V31.56;', 'baseline')
r('const APP_VERSION = "31.55";', 'const APP_VERSION = "31.56";', 'APP_VERSION')
r("version: 'V31.55',", "version: 'V31.56',", 'quality version')

frame_pattern = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
match = frame_pattern.search(text)
if not match:
    raise SystemExit('alternate View iframe not found')
np = html.unescape(match.group(2))

# Remove the duplicate expanded Nazdreg header line. Keep the live primary
# Nazdreg row plus Waha, Deep Strike, Weapon header, Weapons, and tags.
np, removed_detail = re.subn(
    r"(function addExpandedUnitMock\(f\)\{\s*)const h=document\.createElement\('div'\);h\.className='detail-unit-header';.*?f\.appendChild\(h\);\s*",
    r"\1",
    np,
    count=1,
    flags=re.S,
)
if removed_detail != 1:
    raise SystemExit(f'duplicate Nazdreg detail line: expected 1 match, found {removed_detail}')

# Remove the lower MAIN navigation button entirely. VIEW / EDIT / CARDS remain.
np, removed_main = re.subn(
    r"(function addPageNavigation\(f,p\)\{.*?f\.appendChild\(m\));const b=document\.createElement\('button'\);b\.type='button';b\.className='button-standard top-main-button'\+\(p==='main'\?' active-green':''\);b\.textContent='MAIN';b\.onclick=\(\)=>renderPage\('main'\);f\.appendChild\(b\)\}",
    r"\1}",
    np,
    count=1,
    flags=re.S,
)
if removed_main != 1:
    raise SystemExit(f'MAIN button removal: expected 1 match, found {removed_main}')

# Ensure the requested removals are real DOM removals, not merely hidden UI.
if "h.className='detail-unit-header'" in np:
    raise SystemExit('duplicate detail-unit-header creation still present')
if "b.textContent='MAIN'" in np:
    raise SystemExit('MAIN navigation button creation still present')
for required in [
    "w.className='button-standard detail-waha'",
    "ds.className='detail-deep-strike'",
    "wh.className='weapon-header'",
    "function selectWeapon(index)",
    "weaponRow.onclick=e=>{e.stopPropagation();selectWeapon(i)};",
]:
    if required not in np:
        raise SystemExit('preservation check failed: ' + required)

np_srcdoc = html.escape(np, quote=True)
text = text[:match.start(2)] + np_srcdoc + text[match.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.56
    Scope: Remove the duplicate second Nazdreg header/stat line from the alternate View expanded content and delete the lower MAIN navigation button. The primary live Nazdreg row, Waha, Deep Strike, compact Weapon header/rows, Weapon filtering, selection-to-row-10 behavior, and muted non-selected Weapon styling remain unchanged.
    Risk areas: Alternate View duplicate expanded Unit header and lower MAIN button only. Live data wiring, Weapon interactions, View/Edit/Cards navigation, roster persistence, and combat behavior are unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.55\n'
if mark not in text:
    raise SystemExit('release note marker missing')
text = text.replace(mark, note + mark, 1)
text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.51\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

checks = [
    '<title>WH40k 11th V31.56</title>',
    'const APP_VERSION = "31.56";',
    "version: 'V31.56',",
    "w.className=&#x27;button-standard detail-waha&#x27;",
    "function selectWeapon(index)",
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))
if "h.className=&#x27;detail-unit-header&#x27;" in text:
    raise SystemExit('duplicate Nazdreg line still encoded in final HTML')
if "b.textContent=&#x27;MAIN&#x27;" in text:
    raise SystemExit('MAIN button still encoded in final HTML')

out.write_text(text, encoding='utf-8')
print('Built V31.56 without duplicate Nazdreg line or lower MAIN button')
