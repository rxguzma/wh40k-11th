from pathlib import Path
import html
import re

path = Path('WH40k_11th.html')
text = path.read_text(encoding='utf-8')


def once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


# Sequential release metadata.
once('<title>WH40k 11th V31.99</title>', '<title>WH40k 11th V31.100</title>', 'title')
once('The current baseline is WH40k_11th_V31.99;', 'The current baseline is WH40k_11th_V31.100;', 'baseline')
once('const APP_VERSION = "31.99";', 'const APP_VERSION = "31.100";', 'APP_VERSION')
once("version: 'V31.99',", "version: 'V31.100',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('New View iframe missing')
view_np = html.unescape(vm.group(2))

# Reuse already-loaded live data across local VIEW/EDIT switches.
old_state = "let frozenNewViewSnapshot=null;\nlet currentViewRosterRows=[];\nfunction cloneNewViewValue(value){"
new_state = "let frozenNewViewSnapshot=null;\nlet currentViewRosterRows=[];\nlet cachedLiveViewHeader=null;\nlet hasLiveViewCache=false;\nfunction cloneNewViewValue(value){"
once(old_state, new_state, 'New View live-cache state')

# The existing parent screen-open path refreshes the header before the roster.
# Capture that already-rendered live header when the roster refresh completes,
# so a local VIEW/EDIT switch does not need another parent/model header read.
old_roster_refresh = r'''function refreshAlternateViewUnitsFromParent(){if(newViewProcessingLocked())return false;
  let rows=[];
  try{rows=parent&&typeof parent.getAlternateViewRosterRows==='function'?parent.getAlternateViewRosterRows():[]}catch(_){rows=[]}
  return renderNewViewRosterRows(rows);
}
window.refreshAlternateViewUnitsFromParent=refreshAlternateViewUnitsFromParent;'''
new_roster_refresh = r'''function refreshAlternateViewUnitsFromParent(){if(newViewProcessingLocked())return false;
  let rows=[];
  try{rows=parent&&typeof parent.getAlternateViewRosterRows==='function'?parent.getAlternateViewRosterRows():[]}catch(_){rows=[]}
  const ok=renderNewViewRosterRows(rows);
  cachedLiveViewHeader=captureNewViewHeaderSnapshot();
  hasLiveViewCache=true;
  return ok;
}
window.refreshAlternateViewUnitsFromParent=refreshAlternateViewUnitsFromParent;'''
once(old_roster_refresh, new_roster_refresh, 'New View roster/header cache validity')

# Split EDIT rendering from EDIT live refresh so the local toggle can reuse the
# existing ordered rows instead of walking the full parent model again.
unified_pat = re.compile(r'function refreshUnifiedEditRows\(\)\{.*?window\.refreshUnifiedEdit=refreshUnifiedEdit;', re.S)
um = unified_pat.search(view_np)
if not um:
    raise SystemExit('Unified Edit refresh block missing')
new_unified = r'''function renderUnifiedEditRows(rows){
  rows=Array.isArray(rows)?rows:[];
  grid.querySelectorAll('.dynamic-roster-row').forEach(el=>el.remove());
  let cursor=FIRST_UNIT_ROW;
  rows.forEach((data,rowIndex)=>{
    if(data&&data.kind==='spacer'){
      const spacer=document.createElement('div');
      spacer.className='roster-spacer-row dynamic-roster-row';
      spacer.dataset.rosterIndex=String(rowIndex);
      spacer.style.gridRow=String(cursor++);
      grid.appendChild(spacer);
      return;
    }
    if(!data||data.kind!=='unit')return;
    const f=document.createDocumentFragment();
    const row=addUnifiedEditUnit(f,data,rowIndex);
    row.style.gridRow=String(cursor++);
    grid.appendChild(f);
  });
  const mainButton=grid.querySelector('.top-main-button');
  if(mainButton)mainButton.style.gridRow=String(cursor+1);
  const sheetPoints=rows.reduce((sum,row)=>{
    if(!row||row.kind!=='unit')return sum;
    const value=Number(row.points);
    return sum+(Number.isFinite(value)?Math.max(0,value):0);
  },0);
  const titlePoints=grid.querySelector('.top-summary-rest');
  if(titlePoints)titlePoints.textContent='- '+String(sheetPoints)+' pts';
  return rows.some(row=>row&&row.kind==='unit');
}
function refreshUnifiedEditRows(){
  let rows=[];
  try{rows=parent&&typeof parent.getAlternateViewRosterRows==='function'?parent.getAlternateViewRosterRows():[]}catch(_){rows=[]}
  rows=Array.isArray(rows)?rows:[];
  currentViewRosterRows=rows;
  cachedLiveViewHeader=captureNewViewHeaderSnapshot();
  hasLiveViewCache=true;
  return renderUnifiedEditRows(rows);
}
window.refreshUnifiedEditRows=refreshUnifiedEditRows;
function refreshUnifiedEdit(){
  refreshNewViewTitleFromLegacy();
  return refreshUnifiedEditRows();
}
window.refreshUnifiedEdit=refreshUnifiedEdit;'''
view_np = view_np[:um.start()] + new_unified + view_np[um.end():]

# Build the fixed 40x16 grid background once. On a local mode switch remove only
# mode content and reuse cached data synchronously. Initial/live refreshes still
# use the existing parent/model entry points.
render_pat = re.compile(r"function renderPage\(p\)\{.*?\}\nrenderPage\('view'\);", re.S)
rm = render_pat.search(view_np)
if not rm:
    raise SystemExit('New View renderPage block missing')
new_render = r'''function ensurePersistentGridCells(){
  if(grid.querySelector('.grid-cell'))return false;
  const background=document.createDocumentFragment();
  addGridCells(background);
  grid.appendChild(background);
  return true;
}
function clearModeContent(){
  Array.from(grid.children).forEach(node=>{
    if(!(node.classList&&node.classList.contains('grid-cell')))node.remove();
  });
  grid.querySelectorAll('.grid-cell[hidden]').forEach(cell=>{cell.hidden=false});
}
function restoreCachedLiveHeader(){
  if(cachedLiveViewHeader)applyNewViewHeaderSnapshot(cachedLiveViewHeader);
}
function renderCachedView(){
  if(!hasLiveViewCache)return false;
  restoreCachedLiveHeader();
  renderNewViewRosterRows(currentViewRosterRows);
  return true;
}
function renderCachedEdit(){
  if(!hasLiveViewCache)return false;
  restoreCachedLiveHeader();
  renderUnifiedEditRows(currentViewRosterRows);
  return true;
}
function renderPage(p){
  activePageMode=p;
  ensurePersistentGridCells();
  clearModeContent();
  grid.setAttribute('aria-label',p[0].toUpperCase()+p.slice(1)+' page layout grid');
  const f=document.createDocumentFragment();
  addPageNavigation(f,p);
  if(p==='view'){
    addViewHeader(f,p);
    addViewStatHeader(f);
    addExpandedUnitMock(f);
  }
  if(p==='edit'){
    addViewHeader(f,p);
    const viewOnly=f.querySelector('.view-filter-toggle');
    if(viewOnly)viewOnly.remove();
  }
  if(p==='main'){
    const b=document.createElement('button');
    b.type='button';b.className='button-standard sample-button-standard';b.textContent='BUTTON';f.appendChild(b);
    const g=document.createElement('button');
    g.type='button';g.className='button-standard sample-button-green';g.textContent='GREEN';f.appendChild(g);
    [['font-sample font-sample-title','20PX ROBOTO'],['font-sample font-sample-body','14PX ROBOTO'],['font-sample font-sample-meta','12PX ROBOTO']].forEach(([c,t])=>{const x=document.createElement('div');x.className=c;x.textContent=t;f.appendChild(x)});
  }
  grid.appendChild(f);

  if(p==='view'){
    if(newViewProcessingLocked())renderFrozenNewView();
    else if(!renderCachedView())requestAnimationFrame(refreshNewView);
  }
  if(p==='edit'){
    // The VIEW lock remains scoped to VIEW. Entering EDIT from a locked VIEW
    // preserves the established live EDIT refresh rather than using frozen data.
    if(newViewHeaderLocked)requestAnimationFrame(refreshUnifiedEdit);
    else if(!renderCachedEdit())requestAnimationFrame(refreshUnifiedEdit);
  }
}
renderPage('view');'''
view_np = view_np[:rm.start()] + new_render + view_np[rm.end():]

text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.100
    Scope: Make the unified New View VIEW/EDIT toggle a true local fast path. The 40x16 coordinate/grid background is now created once and retained across mode switches instead of deleting and recreating 640 grid cells on every tap. Normal unlocked VIEW and EDIT switches reuse the already-loaded header and ordered roster rows in memory, so switching modes no longer re-runs getAlternateViewHeaderData/getAlternateViewRosterRows merely because the display mode changed. Live refresh entry points remain available and update the cache when New View is opened/refreshed from the parent. The VIEW lock contract is preserved: locked VIEW uses its frozen snapshot, while entering EDIT from a locked VIEW still performs the established live Edit refresh rather than reusing frozen data.
    Risk areas: New View local mode-switch rendering/caching only. Unified Edit row presentation and points, direct model bridges, frozen View lock semantics, Version/Update/Download and version-route restoration, Cards, Old Edit, persistence, CSV data, Waha routing, and Probable remain unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.99\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

notes = list(re.finditer(r'\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n', text, re.S))
for match in reversed(notes[5:]):
    text = text[:match.start()] + text[match.end():]

# Final acceptance checks.
vm = view_pat.search(text)
if not vm:
    raise SystemExit('New View iframe missing after writeback')
final_view = html.unescape(vm.group(2))
required_view = [
    'let cachedLiveViewHeader=null;',
    'let hasLiveViewCache=false;',
    'function ensurePersistentGridCells()',
    'function clearModeContent()',
    'function renderCachedView()',
    'function renderCachedEdit()',
    'function renderUnifiedEditRows(rows)',
    "if(grid.querySelector('.grid-cell'))return false;",
    'addGridCells(background);',
    "grid.querySelectorAll('.grid-cell[hidden]').forEach",
    'currentViewRosterRows=rows;',
    'cachedLiveViewHeader=captureNewViewHeaderSnapshot();',
    'hasLiveViewCache=true;',
    "else if(!renderCachedView())requestAnimationFrame(refreshNewView)",
    "else if(!renderCachedEdit())requestAnimationFrame(refreshUnifiedEdit)",
    'if(newViewHeaderLocked)requestAnimationFrame(refreshUnifiedEdit);',
    "toggle.onclick=()=>renderPage(p==='view'?'edit':'view')",
    'function renderFrozenNewView()',
]
for value in required_view:
    if value not in final_view:
        raise SystemExit('V31.100 New View acceptance failed: ' + value)
for forbidden in ['grid.replaceChildren()', "function renderPage(p){activePageMode=p;grid.replaceChildren()"]:
    if forbidden in final_view:
        raise SystemExit('V31.100 old full-rebuild toggle path remains: ' + forbidden)
if final_view.count('addGridCells(background);') != 1:
    raise SystemExit('V31.100 persistent grid build count is not exactly one')

required_outer = [
    '<title>WH40k 11th V31.100</title>',
    'The current baseline is WH40k_11th_V31.100;',
    'const APP_VERSION = "31.100";',
    "version: 'V31.100',",
    'CHANGE NOTE - WH40k_11th_V31.100',
    'window.parent.__wh40kRestoreAppScreen = "newpage";',
]
for value in required_outer:
    if value not in text:
        raise SystemExit('V31.100 acceptance failed: ' + value)
for forbidden in ['id="newEditPageScreen"','id="npEditFrame"','window.getNewEditRosterRows','window.getNewEditHeaderData']:
    if forbidden in text:
        raise SystemExit('V31.100 regressed retired standalone New Edit: ' + forbidden)

path.write_text(text, encoding='utf-8')
print('Built V31.100: persistent grid plus cached local VIEW/EDIT switching')
