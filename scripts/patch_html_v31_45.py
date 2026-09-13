from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.44.html')
np_src = Path('Np1.37.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')
np = np_src.read_text(encoding='utf-8')


def r(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


r('<title>WH40k 11th V31.44</title>', '<title>WH40k 11th V31.45</title>', 'title')
r('The current baseline is WH40k_11th_V31.44;', 'The current baseline is WH40k_11th_V31.45;', 'baseline')
r('const APP_VERSION = "31.44";', 'const APP_VERSION = "31.45";', 'APP_VERSION')
r("version: 'V31.44',", "version: 'V31.45',", 'quality version')

# Keep Np1.37 itself as the alternate View surface so geometry, fonts, sizes,
# colors, spans, and blank rows are not reinterpreted during transfer.
np = np.replace(
    '</style>',
    '''\n.grid-toggle{grid-column:1;grid-row:6;z-index:102;align-self:center;justify-self:center;width:var(--std)!important;height:var(--std)!important;padding:0!important}\n.draft-grid{border-top:0;border-left:0}\n.grid-cell{visibility:hidden}\n.draft-grid.grid-on{border-top:1px solid rgba(158,203,255,.25);border-left:1px solid rgba(158,203,255,.25)}\n.draft-grid.grid-on .grid-cell{visibility:visible}\n.version-bar{display:none!important}\n</style>''',
    1,
)
np = np.replace('b.onclick=()=>renderPage(t);', 'b.onclick=()=>parent.UI.selectAppMode(t);', 1)
np = np.replace("b.onclick=()=>renderPage('main');", "b.onclick=()=>parent.UI.selectAppMode('view');", 1)
old_phase = "const ph=document.createElement('div');ph.className='phase-buttons';['COMMAND','MOVE','SHOOT','CHARGE','FIGHT'].forEach(l=>{const b=document.createElement('button');b.type='button';b.className='button-standard';b.textContent=l;ph.appendChild(b)});f.appendChild(ph)"
new_phase = "const gb=document.createElement('button');gb.type='button';gb.className='button-standard grid-toggle';gb.textContent='G';gb.setAttribute('aria-label','Toggle grid');gb.setAttribute('aria-pressed','false');gb.onclick=()=>{const on=!grid.classList.contains('grid-on');grid.classList.toggle('grid-on',on);gb.classList.toggle('active-green',on);gb.setAttribute('aria-pressed',on?'true':'false')};f.appendChild(gb);const ph=document.createElement('div');ph.className='phase-buttons';['COMMAND','MOVE','SHOOT','CHARGE','FIGHT'].forEach(l=>{const b=document.createElement('button');b.type='button';b.className='button-standard';b.textContent=l;ph.appendChild(b)});f.appendChild(ph)"
if old_phase not in np:
    raise SystemExit('Np phase-row marker missing')
np = np.replace(old_phase, new_phase, 1)

# The iframe is same-origin srcdoc. It is the actual Np1.37 View markup/CSS,
# embedded into the real HTML, with only the requested navigation + Grid toggle changes.
np_srcdoc = html.escape(np, quote=True)

css_pattern = re.compile(r'\n    /\* V31\.43 alternate View:.*?\.np-view-phase-buttons\{.*?\}\n', re.S)
replacement_css = '''\n    /* V31.45: Np1.37 is embedded directly so its 16 x 26px geometry remains authoritative. */\n    body.np-view-screen-active .app-sticky-header{display:none}\n    .np-view-screen{width:100%;min-height:100vh;min-height:100dvh;margin:0!important;padding:env(safe-area-inset-top) 0 env(safe-area-inset-bottom)!important;background:#0f1115;overflow-x:hidden}\n    .np-view-frame{display:block;width:416px;height:806px;margin:0 auto;border:0;background:#0f1115}\n'''
text, count = css_pattern.subn(replacement_css, text, count=1)
if count != 1:
    raise SystemExit(f'alternate View CSS replacement: expected 1 match, found {count}')

screen_pattern = re.compile(
    r'  <div id="newPageScreen" class="screen np-view-screen" aria-label="Alternate View page">.*?\n  </div>\n\n\n  <div id="cardsScreen" class="screen">',
    re.S,
)
screen = f'''  <div id="newPageScreen" class="screen np-view-screen" aria-label="Alternate View page">\n    <iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc="{np_srcdoc}"></iframe>\n  </div>\n\n\n  <div id="cardsScreen" class="screen">'''
text, count = screen_pattern.subn(screen, text, count=1)
if count != 1:
    raise SystemExit(f'alternate View screen replacement: expected 1 match, found {count}')

note = '''  <!--\n    CHANGE NOTE - WH40k_11th_V31.45\n    Scope: Transfer the complete Np1.37 View surface into the real HTML without reconstructing its layout. The real HTML embeds the Np1.37 source directly, preserving its exact 16-column x 26px, 31-row geometry, fonts, sizes, colors, spans, blank rows, sample Unit rows, expanded Nazdreg detail, Main button, Weapon table, all five Weapons, and Tags. Add a one-cell Grid button at A6 immediately left of COMMAND; grid lines and coordinates are off by default and toggle on/off using the original pale-blue drafting overlay. Alternate View/Edit/Cards/Main controls route back to the existing real app screens.\n    Risk areas: Alternate View surface only. Canonical View/Edit/Cards, roster data, persistence, and combat behavior are unchanged.\n  -->\n\n'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.44\n'
if mark not in text:
    raise SystemExit('release note marker missing')
text = text.replace(mark, note + mark, 1)
text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.40\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

checks = [
    '<title>WH40k 11th V31.45</title>',
    'const APP_VERSION = "31.45";',
    "version: 'V31.45',",
    'id="npViewFrame" class="np-view-frame"',
    'grid-toggle',
    'grid-column:1;grid-row:6',
    'draft-grid.grid-on',
    'RAPID FIRE 2',
    'IGNORES COVER',
    'Kustom Blasta X – Gatler',
    'Moonchewa',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))

out.write_text(text, encoding='utf-8')
print('Built V31.45 by embedding exact Np1.37 View with Grid toggle')
