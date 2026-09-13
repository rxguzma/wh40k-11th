from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.46.html')
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


def nr(old: str, new: str, label: str) -> None:
    global np
    count = np.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    np = np.replace(old, new, 1)


r('<title>WH40k 11th V31.46</title>', '<title>WH40k 11th V31.47</title>', 'title')
r('The current baseline is WH40k_11th_V31.46;', 'The current baseline is WH40k_11th_V31.47;', 'baseline')
r('const APP_VERSION = "31.46";', 'const APP_VERSION = "31.47";', 'APP_VERSION')
r("version: 'V31.46',", "version: 'V31.47',", 'quality version')

# Start from the exact Np1.37 surface. Preserve the V31.46 ten-row insertion,
# but move the one-row View/Edit/Cards menu from row 4 to row 2.
nr(
    ".top-mode-buttons{grid-column:11/span 6;grid-row:2/span 2;z-index:4;display:grid;grid-template-columns:repeat(3,calc(var(--cell)*2));align-items:center;justify-items:center}.top-mode-buttons .button-standard{height:calc((var(--cell)*2) - var(--gap))}.top-main-button{grid-column:15/span 2;grid-row:15;z-index:4;align-self:center;justify-self:center}.phase-buttons{grid-column:2/span 15;grid-row:6;z-index:3;display:grid;grid-template-columns:repeat(5,calc(var(--cell)*3));align-items:center;justify-items:center}",
    ".top-mode-buttons{grid-column:11/span 6;grid-row:2;z-index:4;display:grid;grid-template-columns:repeat(3,calc(var(--cell)*2));align-items:center;justify-items:center}.top-mode-buttons .button-standard{height:var(--std)}.top-main-button{grid-column:15/span 2;grid-row:25;z-index:4;align-self:center;justify-self:center}.phase-buttons{grid-column:2/span 15;grid-row:6;z-index:3;display:grid;grid-template-columns:repeat(5,calc(var(--cell)*3));align-items:center;justify-items:center}",
    'navigation row 2 and shifted Main',
)

nr(
    ".view-unit-row-first{grid-row:9}.view-unit-row-second{grid-row:10}.edit-unit-row-first{grid-row:9}.edit-unit-row-second{grid-row:10}",
    ".view-unit-row-first{grid-row:9}.view-unit-row-second{grid-row:20}.edit-unit-row-first{grid-row:9}.edit-unit-row-second{grid-row:20}",
    'Meganobz row 20',
)
nr('grid-row:13;z-index:3;display:grid;', 'grid-row:23;z-index:3;display:grid;', 'detail row 23')
nr('grid-row:14;z-index:3;align-self:center;', 'grid-row:24;z-index:3;align-self:center;', 'deep strike row 24')
nr('.weapon-header{grid-row:17;', '.weapon-header{grid-row:27;', 'weapon header row 27')
nr(
    '.weapon-row-1{grid-row:18}.weapon-tags-1{grid-row:19}.weapon-row-2{grid-row:21}.weapon-tags-2{grid-row:22}.weapon-row-3{grid-row:24}.weapon-tags-3{grid-row:25}.weapon-row-4{grid-row:27}.weapon-tags-4{grid-row:28}.weapon-row-5{grid-row:30}.weapon-tags-5{grid-row:31}',
    '.weapon-row-1{grid-row:28}.weapon-tags-1{grid-row:29}.weapon-row-2{grid-row:31}.weapon-tags-2{grid-row:32}.weapon-row-3{grid-row:34}.weapon-tags-3{grid-row:35}.weapon-row-4{grid-row:37}.weapon-tags-4{grid-row:38}.weapon-row-5{grid-row:40}.weapon-tags-5{grid-row:41}',
    'shift weapon rows by 10',
)
nr('.sample-button-standard{grid-column:2/span 3;grid-row:24;', '.sample-button-standard{grid-column:2/span 3;grid-row:34;', 'sample button row 34')
nr('.sample-button-green{grid-column:2/span 2;grid-row:25;', '.sample-button-green{grid-column:2/span 2;grid-row:35;', 'sample green row 35')
nr('.font-sample-title{grid-row:26;', '.font-sample-title{grid-row:36;', 'font title row 36')
nr('.font-sample-body{grid-row:27;', '.font-sample-body{grid-row:37;', 'font body row 37')
nr('.font-sample-meta{grid-row:28;', '.font-sample-meta{grid-row:38;', 'font meta row 38')
nr('for(let r=1;r<=31;r++)', 'for(let r=1;r<=41;r++)', '41 grid rows')

# Preserve real-app navigation, the A6 Grid toggle, hidden-by-default drafting grid,
# and hidden standalone NP version controls.
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

# Only the first View row (Nazdreg) is live. Meganobz and all other transferred
# content remain the original static Np1.37 mock.
nr(
    "addViewUnit(f,'view-unit-row-first','Nazdreg','',['5\"','7','2+/5++','8','6+','1']);",
    "addViewUnit(f,'view-unit-row-first','Nazdreg','',['','','','','','']);",
    'blank static Nazdreg stats',
)

live_helper = '''\nfunction refreshNazdregFromParent(){\n  const row=grid.querySelector('.view-unit-row-first');\n  if(!row)return false;\n  let data=null;\n  try{data=parent&&typeof parent.getAlternateViewNazdregData==='function'?parent.getAlternateViewNazdregData():null}catch(_){data=null}\n  if(!data){row.style.display='none';return false}\n  row.style.display='grid';\n  const name=row.querySelector('.view-unit-name');\n  if(name)name.textContent=String(data.name||'Nazdreg');\n  [data.m,data.t,data.sv,data.w,data.ld,data.oc].forEach((value,index)=>{const cell=row.querySelector('.s'+(index+1));if(cell)cell.textContent=String(value??'')});\n  return true;\n}\nwindow.refreshNazdregFromParent=refreshNazdregFromParent;\n'''
nr('function renderPage(p){', live_helper + 'function renderPage(p){', 'Nazdreg live helper')
nr("}grid.appendChild(f)}\nrenderPage('view');", "}grid.appendChild(f);if(p==='view')requestAnimationFrame(refreshNazdregFromParent)}\nrenderPage('view');", 'refresh Nazdreg after View render')

np_srcdoc = html.escape(np, quote=True)

# Replace the embedded NP document while leaving second-press View routing intact.
frame_pattern = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=").*?(</iframe>)', re.S)
text, count = frame_pattern.subn(lambda m: m.group(1) + np_srcdoc + '"></iframe>', text, count=1)
if count != 1:
    raise SystemExit(f'NP iframe replacement: expected 1 match, found {count}')

# Expose only the requested active-roster/Edit data to the embedded View.
parent_helper = '''    window.getAlternateViewNazdregData = function() {\n      const roster = appEditMode && viewEditRosterDraft ? getViewEditRoster() : getActiveRoster();\n      const models = getRosterEntryModels(roster);\n      const normalize = value => String(value || "").trim().toLowerCase().replace(/[^a-z0-9]+/g, "");\n      const model = models.find(item => {\n        if (!item || item.isSpacer || item.isNote || item.isDeleted || item.isMissingUnit) return false;\n        const candidates = [\n          item.displayName,\n          item.unit && item.unit.name,\n          item.entry && item.entry.unitId,\n          item.unit && item.unit.unitId\n        ].map(normalize).filter(Boolean);\n        return candidates.some(value => value === "nazdreg" || value.endsWith("nazdreg"));\n      });\n      if (!model) return null;\n      const stats = model.stats || {};\n      return {\n        name: String(model.displayName || (model.unit && model.unit.name) || "Nazdreg"),\n        m: String(stats.m ?? ""),\n        t: String(stats.t ?? ""),\n        sv: String(stats.sv ?? ""),\n        w: String(stats.w ?? ""),\n        ld: String(stats.ld ?? ""),\n        oc: String(stats.oc ?? "")\n      };\n    };\n\n'''
r('    function selectAppMode(mode) {', parent_helper + '    function selectAppMode(mode) {', 'parent Nazdreg data bridge')

# Refresh the live row every time the alternate View becomes visible so the latest
# committed Edit values are reflected without touching any other transferred row.
r(
'''      newPageScreen.classList.add("active");\n      document.body.classList.add("np-view-screen-active");\n      activeAppScreen = "newpage";''',
'''      newPageScreen.classList.add("active");\n      document.body.classList.add("np-view-screen-active");\n      activeAppScreen = "newpage";\n\n      const npFrame = document.getElementById("npViewFrame");\n      try {\n        const npWindow = npFrame && npFrame.contentWindow;\n        if (npWindow && typeof npWindow.refreshNazdregFromParent === "function") npWindow.refreshNazdregFromParent();\n      } catch (_) {}''',
'Nazdreg refresh on alternate View open',
)

note = '''  <!--\n    CHANGE NOTE - WH40k_11th_V31.47\n    Scope: Move the transferred View/Edit/Cards menu from row 4 to row 2 while preserving its one-row 24px button geometry. Wire only the first alternate-View Nazdreg row to the real roster/Edit model: Unit name plus effective M, T, SV, W, LD, and OC now refresh from the active roster whenever the alternate View opens. Meganobz and every other transferred row remain static. Preserve the ten-row insertion, 41-row grid, A6 Grid toggle, exact Np1.37 visual standards, and existing second-press View navigation.\n    Risk areas: Alternate View menu position and Nazdreg first-row data bridge only. Canonical View/Edit/Cards, persistence, combat behavior, and other transferred mock content are unchanged.\n  -->\n\n'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.46\n'
if mark not in text:
    raise SystemExit('release note marker missing')
text = text.replace(mark, note + mark, 1)
text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.42\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

checks = [
    '<title>WH40k 11th V31.47</title>',
    'const APP_VERSION = "31.47";',
    "version: 'V31.47',",
    'grid-row:2;z-index:4;display:grid;grid-template-columns:repeat(3,calc(var(--cell)*2))',
    '.view-unit-row-second{grid-row:20}',
    '.weapon-tags-5{grid-row:41}',
    'for(let r=1;r&lt;=41;r++)',
    'height:1066px',
    'grid-toggle',
    'refreshNazdregFromParent',
    'getAlternateViewNazdregData',
    'sv: String(stats.sv ?? "")',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))

out.write_text(text, encoding='utf-8')
print('Built V31.47 with menu on row 2 and live Nazdreg profile row')
