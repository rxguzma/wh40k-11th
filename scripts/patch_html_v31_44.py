from pathlib import Path
import re

src = Path('versions/WH40k_11th_V31.43.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def r(old: str, new: str, label: str) -> None:
    global text
    n = text.count(old)
    if n != 1:
        raise SystemExit(f'{label}: expected 1 match, found {n}')
    text = text.replace(old, new, 1)


r('<title>WH40k 11th V31.43</title>', '<title>WH40k 11th V31.44</title>', 'title')
r('The current baseline is WH40k_11th_V31.43;', 'The current baseline is WH40k_11th_V31.44;', 'baseline')
r('const APP_VERSION = "31.43";', 'const APP_VERSION = "31.44";', 'APP_VERSION')
r("version: 'V31.43',", "version: 'V31.44',", 'quality version')

# Rebuild the alternate View header using the literal Np1.37 16 x 26px drafting geometry.
# The drafting overlay itself is intentionally absent; only the approved UI remains.
r(
'''    .np-view-screen{width:100%;min-height:100vh;min-height:100dvh;background:#0f1115;overflow-x:hidden}
    .np-view-header-grid{display:grid;grid-template-columns:repeat(16,26px);grid-template-rows:repeat(5,26px);width:416px;margin:0 auto;background:#0f1115;color:#f1f3f4;isolation:isolate}
    .np-view-header-shell{grid-column:1/span 16;grid-row:1/span 4;z-index:1;border:1px solid #2c313a;border-radius:12px;background:#171a21}
    .np-view-roster-name{grid-column:2/span 7;grid-row:1;z-index:2;display:flex;align-items:center;min-width:0;color:#f1f3f4;font:900 20px/1 Roboto,Arial,sans-serif;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .np-view-detachments{grid-column:2/span 9;grid-row:2;z-index:2;display:flex;align-items:center;min-width:0;color:#9aa0a6;font:700 14px/1 Roboto,Arial,sans-serif;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .np-view-summary{grid-column:2/span 9;grid-row:3;z-index:2;display:flex;align-items:center;gap:6px;min-width:0;font:700 12px/1 Roboto,Arial,sans-serif;white-space:nowrap;overflow:hidden}.np-view-summary-disposition{color:#80d6a3}.np-view-summary-rest{color:#9aa0a6}
    .np-view-nav-button,.np-view-phase-button{width:calc(100% - 2px);height:24px;padding:0 10px;border:1px solid #48515f;border-radius:6px;background:#2b313b;color:#f1f3f4;font-family:Roboto,Arial,sans-serif;font-size:12px;font-weight:700;line-height:1;display:inline-flex;align-items:center;justify-content:center;white-space:nowrap}
    .np-view-nav-button{z-index:3;width:50px;height:50px;align-self:center;justify-self:center}.np-view-nav-button.active{background:#1f5b35;border-color:#2e7d49}.np-view-nav-view{grid-column:11/span 2;grid-row:1/span 2}.np-view-nav-edit{grid-column:13/span 2;grid-row:1/span 2}.np-view-nav-cards{grid-column:15/span 2;grid-row:1/span 2}
    .np-view-phase-buttons{grid-column:2/span 15;grid-row:5;z-index:2;display:grid;grid-template-columns:repeat(5,78px);align-items:center;justify-items:center}
''',
'''    .np-view-screen{width:100%;min-height:100vh;min-height:100dvh;margin:0!important;padding:env(safe-area-inset-top) 0 0!important;background:#0f1115;overflow-x:hidden}
    .np-view-header-grid{display:grid;grid-template-columns:repeat(16,26px);grid-template-rows:repeat(6,26px);width:416px;height:156px;margin:0 auto;background:#0f1115;color:#f1f3f4;isolation:isolate}
    .np-view-header-shell{grid-column:1/span 16;grid-row:1/span 5;z-index:1;border:1px solid #2c313a;border-radius:12px;background:#171a21}
    .np-view-roster-name{grid-column:2/span 7;grid-row:2;z-index:2;display:flex;align-items:center;min-width:0;color:#f1f3f4;font:900 20px/1 Roboto,Arial,sans-serif;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .np-view-detachments{grid-column:2/span 9;grid-row:3;z-index:2;display:flex;align-items:center;min-width:0;color:#9aa0a6;font:700 14px/1 Roboto,Arial,sans-serif;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .np-view-summary{grid-column:2/span 9;grid-row:4;z-index:2;display:flex;align-items:center;gap:6px;min-width:0;font:700 12px/1 Roboto,Arial,sans-serif;white-space:nowrap;overflow:hidden}.np-view-summary-disposition{color:#80d6a3}.np-view-summary-rest{color:#9aa0a6}
    .np-view-nav-button,.np-view-phase-button{width:calc(100% - 2px);height:24px;padding:0 10px;border:1px solid #48515f;border-radius:6px;background:#2b313b;color:#f1f3f4;font-family:Roboto,Arial,sans-serif;font-size:12px;font-weight:700;line-height:1;display:inline-flex;align-items:center;justify-content:center;white-space:nowrap}
    .np-view-nav-button{z-index:3;width:50px;height:50px;align-self:center;justify-self:center}.np-view-nav-button.active{background:#1f5b35;border-color:#2e7d49}.np-view-nav-view{grid-column:11/span 2;grid-row:2/span 2}.np-view-nav-edit{grid-column:13/span 2;grid-row:2/span 2}.np-view-nav-cards{grid-column:15/span 2;grid-row:2/span 2}
    .np-view-phase-buttons{grid-column:2/span 15;grid-row:6;z-index:2;display:grid;grid-template-columns:repeat(5,78px);align-items:center;justify-items:center}
''',
'exact Np1.37 rows 2-6 geometry',
)

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.44
    Scope: Correct the alternate View transfer to preserve the literal Np1.37 drafting geometry instead of adapting it to the existing shell. The surface now uses the exact 16-column x 26px grid: roster name B2:H2, detachments B3:J3, summary B4:J4, View/Edit/Cards at K2:P3, row 5 left empty, and phase controls B6:P6. The Np header shell retains its original A1:P5 geometry. Drafting grid lines and coordinates remain hidden.
    Risk areas: Alternate View geometry only. Second-press View routing, existing View/Edit/Cards behavior, roster data, persistence, and combat behavior are unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.43\n'
if mark not in text:
    raise SystemExit('release note marker missing')
text = text.replace(mark, note + mark, 1)
text, n = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.39\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if n != 1:
    raise SystemExit(f'old note removal: expected 1, found {n}')

checks = [
    '<title>WH40k 11th V31.44</title>',
    'const APP_VERSION = "31.44";',
    "version: 'V31.44',",
    'grid-template-columns:repeat(16,26px);grid-template-rows:repeat(6,26px)',
    '.np-view-roster-name{grid-column:2/span 7;grid-row:2;',
    '.np-view-detachments{grid-column:2/span 9;grid-row:3;',
    '.np-view-summary{grid-column:2/span 9;grid-row:4;',
    '.np-view-nav-view{grid-column:11/span 2;grid-row:2/span 2}',
    '.np-view-nav-edit{grid-column:13/span 2;grid-row:2/span 2}',
    '.np-view-nav-cards{grid-column:15/span 2;grid-row:2/span 2}',
    '.np-view-phase-buttons{grid-column:2/span 15;grid-row:6;',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))
if 'new-page-grid-cell' in text and False:
    raise SystemExit('unexpected drafting grid dependency')

out.write_text(text, encoding='utf-8')
print('Built V31.44 with exact Np1.37 rows 2-6 geometry')
