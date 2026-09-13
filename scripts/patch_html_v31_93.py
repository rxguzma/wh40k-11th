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
once('<title>WH40k 11th V31.92</title>', '<title>WH40k 11th V31.93</title>', 'title')
once('The current baseline is WH40k_11th_V31.92;', 'The current baseline is WH40k_11th_V31.93;', 'baseline')
once('const APP_VERSION = "31.92";', 'const APP_VERSION = "31.93";', 'APP_VERSION')
once("version: 'V31.92',", "version: 'V31.93',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('New View iframe missing')
view_np = html.unescape(vm.group(2))

# Add a detached frozen snapshot beside the V31.92 processing gate. The snapshot
# contains only data already loaded into New View; locking does not query parent.
old_state = "let newViewHeaderLocked=false;\nlet activePageMode='view';\nfunction newViewProcessingLocked(){return Boolean(newViewHeaderLocked&&activePageMode==='view')}"
new_state = r'''let newViewHeaderLocked=false;
let activePageMode='view';
let frozenNewViewSnapshot=null;
let currentViewRosterRows=[];
function cloneNewViewValue(value){
  if(value===undefined)return undefined;
  if(typeof structuredClone==='function'){
    try{return structuredClone(value)}catch(_){}
  }
  return JSON.parse(JSON.stringify(value));
}
function newViewProcessingLocked(){return Boolean(newViewHeaderLocked&&activePageMode==='view')}
function captureNewViewHeaderSnapshot(){
  const read=selector=>{const el=grid.querySelector(selector);return el?String(el.textContent||''):''};
  return {
    name:read('.top-roster-name'),
    detachments:read('.top-detachments'),
    disposition:read('.top-summary-disposition'),
    rest:read('.top-summary-rest')
  };
}
function applyNewViewHeaderSnapshot(header){
  const data=header||{};
  const write=(selector,value)=>{const el=grid.querySelector(selector);if(el)el.textContent=String(value||'')};
  write('.top-roster-name',data.name);
  write('.top-detachments',data.detachments);
  write('.top-summary-disposition',data.disposition);
  write('.top-summary-rest',data.rest);
}
function captureNewViewSnapshot(){
  const rows=cloneNewViewValue(currentViewRosterRows);
  return {header:captureNewViewHeaderSnapshot(),rows:Array.isArray(rows)?rows:[]};
}
function activateNewViewSnapshot(snapshot){
  const rows=snapshot&&Array.isArray(snapshot.rows)?cloneNewViewValue(snapshot.rows):[];
  currentViewRosterRows=rows;
  unitDataByIndex=[];
  rows.forEach((data,rowIndex)=>{if(data&&data.kind==='unit')unitDataByIndex[rowIndex]=data});
  applyNewViewHeaderSnapshot(snapshot&&snapshot.header);
  return true;
}'''
if view_np.count(old_state) != 1:
    raise SystemExit(f'New View snapshot state anchor: expected 1 match, found {view_np.count(old_state)}')
view_np = view_np.replace(old_state, new_state, 1)

# Refactor roster rendering so live refresh and frozen re-render share exactly
# the same DOM path. Only the live refresh may access the parent/model layer.
view_refresh_start = view_np.find('function refreshAlternateViewUnitsFromParent(){')
view_refresh_end = view_np.find('window.refreshAlternateViewUnitsFromParent=refreshAlternateViewUnitsFromParent;', view_refresh_start)
if view_refresh_start < 0 or view_refresh_end < 0:
    raise SystemExit('New View roster refresh bounds missing')
view_refresh_end += len('window.refreshAlternateViewUnitsFromParent=refreshAlternateViewUnitsFromParent;')
new_refresh_block = r'''function renderNewViewRosterRows(rows){
  rows=Array.isArray(rows)?rows:[];
  currentViewRosterRows=rows;
  unitDataByIndex=[];
  grid.querySelectorAll('.dynamic-roster-row').forEach(el=>el.remove());
  const f=document.createDocumentFragment();
  let cursor=FIRST_UNIT_ROW;
  rows.forEach((data,rowIndex)=>{
    if(data&&data.kind==='spacer'){
      const spacer=document.createElement('div');
      spacer.className='roster-spacer-row dynamic-roster-row';
      spacer.dataset.rosterIndex=String(rowIndex);
      spacer.style.gridRow=String(cursor++);
      f.appendChild(spacer);
      return;
    }
    if(!data||data.kind!=='unit')return;
    unitDataByIndex[rowIndex]=data;
    const before=f.childNodes.length;
    addViewUnit(f,'dynamic-roster-row',String(data.name||''),'',[data.m,data.t,data.sv,data.w,data.ld,data.oc]);
    const row=f.childNodes[before];
    row.dataset.rosterIndex=String(rowIndex);
    row.style.gridRow=String(cursor++);
    row.onclick=()=>toggleUnitDetails(rowIndex);
  });
  grid.appendChild(f);
  if(activeUnitIndex!==null&&!unitDataByIndex[activeUnitIndex])activeUnitIndex=null;
  selectedWeaponIndex=null;
  applyActiveUnitDetails();
  syncUnitDetailVisibility();
  return unitDataByIndex.some(Boolean);
}
function refreshAlternateViewUnitsFromParent(){if(newViewProcessingLocked())return false;
  let rows=[];
  try{rows=parent&&typeof parent.getAlternateViewRosterRows==='function'?parent.getAlternateViewRosterRows():[]}catch(_){rows=[]}
  return renderNewViewRosterRows(rows);
}
window.refreshAlternateViewUnitsFromParent=refreshAlternateViewUnitsFromParent;
function renderFrozenNewView(){
  if(!newViewProcessingLocked()||!frozenNewViewSnapshot)return false;
  applyNewViewHeaderSnapshot(frozenNewViewSnapshot.header);
  const rows=cloneNewViewValue(frozenNewViewSnapshot.rows);
  return renderNewViewRosterRows(Array.isArray(rows)?rows:[]);
}'''
view_np = view_np[:view_refresh_start] + new_refresh_block + view_np[view_refresh_end:]

# Lock transition: capture and detach first, then turn the lock on. Unlock turns
# the lock off first, discards the snapshot, then performs exactly one live sync.
old_click = "lb.onclick=()=>{newViewHeaderLocked=!newViewHeaderLocked;syncNewViewLockButton(lb)}"
new_click = "lb.onclick=()=>{if(newViewHeaderLocked){newViewHeaderLocked=false;frozenNewViewSnapshot=null;syncNewViewLockButton(lb);requestAnimationFrame(refreshNewView);return}const snapshot=captureNewViewSnapshot();frozenNewViewSnapshot=snapshot;activateNewViewSnapshot(snapshot);newViewHeaderLocked=true;syncNewViewLockButton(lb)}"
if view_np.count(old_click) != 1:
    raise SystemExit(f'New View lock click handler: expected 1 match, found {view_np.count(old_click)}')
view_np = view_np.replace(old_click, new_click, 1)

# If VIEW is rebuilt while still locked, restore only the frozen header/rows.
# No parent/model refresh is allowed in this branch.
old_post = "if(p==='view'){requestAnimationFrame(refreshNewView)}"
new_post = "if(p==='view'){requestAnimationFrame(()=>{if(newViewProcessingLocked())renderFrozenNewView();else refreshNewView()})}"
if view_np.count(old_post) != 1:
    raise SystemExit(f'New View post-render snapshot branch: expected 1 match, found {view_np.count(old_post)}')
view_np = view_np.replace(old_post, new_post, 1)

# Write the modified New View document back.
view_srcdoc = html.escape(view_np, quote=True)
text = text[:vm.start(2)] + view_srcdoc + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.93
    Scope: Add the frozen New View snapshot behind the existing lock. Pressing Lock now copies the already-loaded New View header and ordered roster records into detached in-memory data before the lock state turns on, then rebinds Unit detail/Weapon/Ability interactions to those copied records. While locked, parent/model header and roster refresh entry points remain blocked by the V31.92 gate. If VIEW is re-rendered while still locked, its header and Unit rows are rebuilt only from the frozen snapshot. Range/Melee/Other/All and Unit open/close therefore continue to work against frozen data without requesting new roster/model data. Pressing Unlock turns the lock off, discards the snapshot, and schedules exactly one normal New View synchronization.
    Risk areas: New View in-memory roster/header state and lock/unlock transition only. Existing lock icon/placement, unified Edit behavior, Old Edit, Cards, persistence, CSV data, Waha routing, and Probable remain unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.92\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

# Retain only the five newest V31 detailed notes.
notes = list(re.finditer(r'\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n', text, re.S))
for match in reversed(notes[5:]):
    text = text[:match.start()] + text[match.end():]

# Final acceptance checks.
vm = view_pat.search(text)
if not vm:
    raise SystemExit('New View iframe missing after writeback')
final_view = html.unescape(vm.group(2))
required_view = [
    'let frozenNewViewSnapshot=null;',
    'let currentViewRosterRows=[];',
    'function captureNewViewSnapshot()',
    'function activateNewViewSnapshot(snapshot)',
    'function renderNewViewRosterRows(rows)',
    'function renderFrozenNewView()',
    "parent.getAlternateViewRosterRows==='function'",
    'frozenNewViewSnapshot=snapshot;activateNewViewSnapshot(snapshot);newViewHeaderLocked=true;',
    'newViewHeaderLocked=false;frozenNewViewSnapshot=null;',
    'requestAnimationFrame(refreshNewView)',
    "if(p==='view'){requestAnimationFrame(()=>{if(newViewProcessingLocked())renderFrozenNewView();else refreshNewView()})}",
]
for value in required_view:
    if value not in final_view:
        raise SystemExit('V31.93 New View snapshot acceptance failed: ' + value)

# Locked snapshot helpers must not access parent/model data.
for fn_name in ['captureNewViewSnapshot', 'activateNewViewSnapshot', 'renderFrozenNewView']:
    match = re.search(r'function '+fn_name+r'\([^)]*\)\{(.*?)\n\}', final_view, re.S)
    if not match:
        raise SystemExit('V31.93 helper verification missing: ' + fn_name)
    if 'parent' in match.group(1) or 'getAlternateView' in match.group(1):
        raise SystemExit('V31.93 frozen helper reaches parent/model: ' + fn_name)

# V31.92 direct refresh gates must remain in place.
if final_view.count('if(newViewProcessingLocked())return false;') < 3:
    raise SystemExit('V31.93 regressed one or more V31.92 processing gates')
if "if(p==='edit'){requestAnimationFrame(refreshNewViewTitleFromLegacy);requestAnimationFrame(refreshUnifiedEditRows)}" not in final_view:
    raise SystemExit('V31.93 unified EDIT refresh path changed unexpectedly')

required_outer = [
    '<title>WH40k 11th V31.93</title>',
    'const APP_VERSION = "31.93";',
    "version: 'V31.93',",
    'CHANGE NOTE - WH40k_11th_V31.93',
]
for value in required_outer:
    if value not in text:
        raise SystemExit('V31.93 acceptance failed: ' + value)

path.write_text(text, encoding='utf-8')
print('Built V31.93: New View lock now uses a detached frozen snapshot')
