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
once('<title>WH40k 11th V31.102</title>', '<title>WH40k 11th V31.103</title>', 'title')
once('The current baseline is WH40k_11th_V31.102;', 'The current baseline is WH40k_11th_V31.103;', 'baseline')
once('const APP_VERSION = "31.102";', 'const APP_VERSION = "31.103";', 'APP_VERSION')
once("version: 'V31.102',", "version: 'V31.103',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing')
view_np = html.unescape(vm.group(2))

# Current lock/filter/persistent-grid contracts must exist before this pass.
required_baseline = [
    'let frozenNewViewSnapshot=null;',
    'let currentViewRosterRows=[];',
    'function newViewProcessingLocked()',
    'function captureNewViewSnapshot()',
    'function applyActiveUnitDetails()',
    'function syncUnitDetailVisibility()',
    'function cycleWeaponFilter()',
    'weaponFilterModes',
    'function ensurePersistentGridCells()',
    'function clearModeContent()',
    'function renderFrozenNewView()',
]
for value in required_baseline:
    if value not in view_np:
        raise SystemExit('V31.103 baseline contract missing: ' + value)

# Locked View gets prepared DOM states. Original live View nodes stay mounted but
# hidden while locked; each Unit x filter combination is rendered once BEFORE the
# lock flips on, cloned, and retained as a display-only state.
style_marker = '</style>'
lock_css = '''
.new-view-lock-original-hidden{display:none!important}
.new-view-locked-state{display:contents}
.new-view-locked-state[hidden]{display:none!important}
.new-view-lock-disabled{opacity:.45!important;pointer-events:none!important}
'''
if view_np.count(style_marker) < 1:
    raise SystemExit('Unified New View style close marker missing')
view_np = view_np.replace(style_marker, lock_css + style_marker, 1)

helper_marker = 'function addViewHeader(f,p)'
if view_np.count(helper_marker) != 1:
    raise SystemExit(f'New View header helper marker: expected 1 match, found {view_np.count(helper_marker)}')

lock_helpers = r'''let lockedViewStateCache=null;
let lockedViewStateLayers=[];
let lockedViewFilterOrder=[];
function lockedViewStateKey(unitIndex,mode){
  return (unitIndex===null?'none':String(unitIndex))+'|'+String(mode||'');
}
function getLockedViewFilterOrder(){
  const modes=[];
  if(typeof weaponFilterModes!=='undefined'&&Array.isArray(weaponFilterModes)){
    weaponFilterModes.forEach(mode=>{const value=String(mode||'');if(value&&!modes.includes(value))modes.push(value)});
  }
  const current=String(weaponFilterMode||'');
  if(current&&!modes.includes(current))modes.unshift(current);
  return modes.length?modes:[current||'ALL'];
}
function getLockedViewUnitIndexes(){
  const indexes=[];
  unitDataByIndex.forEach((data,index)=>{if(data)indexes.push(index)});
  return indexes;
}
function primeLockedViewLayer(layer){
  layer.querySelectorAll('.new-view-lock-toggle').forEach(button=>{
    button.classList.add('locked');
    button.classList.remove('unlocked');
    button.innerHTML=newViewLockIcon(true);
    button.setAttribute('title','Unlock');
    button.setAttribute('aria-label','Unlock');
    button.setAttribute('aria-pressed','true');
  });
  layer.querySelectorAll('button,a,[role="button"]').forEach(control=>{
    const marker=[control.id,control.className,control.textContent,control.getAttribute('aria-label')].join(' ').toLowerCase();
    if(marker.includes('probable')){
      control.classList.add('new-view-lock-disabled');
      control.setAttribute('aria-disabled','true');
      if('disabled' in control)control.disabled=true;
    }
  });
}
function cloneLockedViewState(unitIndex,mode){
  const layer=document.createElement('div');
  layer.className='new-view-locked-state';
  layer.dataset.lockStateKey=lockedViewStateKey(unitIndex,mode);
  layer.hidden=true;
  Array.from(grid.children).forEach(node=>{
    if(node.classList&&node.classList.contains('grid-cell'))return;
    if(node.classList&&node.classList.contains('new-view-locked-state'))return;
    layer.appendChild(node.cloneNode(true));
  });
  primeLockedViewLayer(layer);
  return layer;
}
function renderLockedViewCombination(unitIndex,mode){
  activeUnitIndex=unitIndex;
  weaponFilterMode=mode;
  selectedWeaponIndex=null;
  const filter=grid.querySelector('.view-filter-toggle');
  if(filter)filter.textContent=String(mode||'');
  applyActiveUnitDetails();
  syncUnitDetailVisibility();
  if(typeof positionNewViewVersionControls==='function')positionNewViewVersionControls();
}
function clearLockedViewPreparedDom(){
  lockedViewStateLayers.forEach(layer=>{if(layer&&layer.parentNode)layer.remove()});
  lockedViewStateLayers=[];
  lockedViewStateCache=null;
  lockedViewFilterOrder=[];
  Array.from(grid.children).forEach(node=>{
    if(node.classList)node.classList.remove('new-view-lock-original-hidden');
  });
}
function buildLockedViewPreparedDom(){
  clearLockedViewPreparedDom();
  const savedUnit=activeUnitIndex;
  const savedMode=weaponFilterMode;
  lockedViewFilterOrder=getLockedViewFilterOrder();
  const unitIndexes=[null,...getLockedViewUnitIndexes()];
  const cache=new Map();
  const layers=[];
  if(typeof newViewVersionHistoryOpen!=='undefined')newViewVersionHistoryOpen=false;
  if(typeof clearNewViewVersionHistoryButtons==='function')clearNewViewVersionHistoryButtons();
  unitIndexes.forEach(unitIndex=>{
    lockedViewFilterOrder.forEach(mode=>{
      renderLockedViewCombination(unitIndex,mode);
      const layer=cloneLockedViewState(unitIndex,mode);
      cache.set(lockedViewStateKey(unitIndex,mode),layer);
      layers.push(layer);
    });
  });
  renderLockedViewCombination(savedUnit,savedMode);
  lockedViewStateCache=cache;
  lockedViewStateLayers=layers;
  const originals=Array.from(grid.children).filter(node=>!(node.classList&&node.classList.contains('grid-cell')));
  originals.forEach(node=>node.classList&&node.classList.add('new-view-lock-original-hidden'));
  const fragment=document.createDocumentFragment();
  layers.forEach(layer=>fragment.appendChild(layer));
  grid.appendChild(fragment);
  selectedWeaponIndex=null;
  showLockedViewPreparedState(savedUnit,savedMode);
  return true;
}
function showLockedViewPreparedState(unitIndex,mode){
  if(!lockedViewStateCache)return false;
  let target=lockedViewStateCache.get(lockedViewStateKey(unitIndex,mode));
  if(!target){
    target=lockedViewStateCache.get(lockedViewStateKey(null,mode))||lockedViewStateLayers[0]||null;
    unitIndex=null;
  }
  if(!target)return false;
  lockedViewStateLayers.forEach(layer=>{layer.hidden=layer!==target});
  activeUnitIndex=unitIndex;
  weaponFilterMode=mode;
  selectedWeaponIndex=null;
  return true;
}
function beginLockedViewPreparedMode(){
  if(activePageMode!=='view'||newViewHeaderLocked)return false;
  const snapshot=captureNewViewSnapshot();
  frozenNewViewSnapshot=snapshot;
  activateNewViewSnapshot(snapshot);
  try{
    if(!buildLockedViewPreparedDom())throw new Error('Locked View preparation failed');
  }catch(_){
    clearLockedViewPreparedDom();
    frozenNewViewSnapshot=null;
    return false;
  }
  // Lock becomes true only after every prepared state is built and mounted.
  newViewHeaderLocked=true;
  return true;
}
function endLockedViewPreparedMode(){
  if(!newViewHeaderLocked)return false;
  // Unlock first, then discard prepared state and perform one fresh live sync.
  newViewHeaderLocked=false;
  clearLockedViewPreparedDom();
  frozenNewViewSnapshot=null;
  const lockButton=grid.querySelector('.new-view-lock-toggle');
  if(lockButton)syncNewViewLockButton(lockButton);
  return refreshNewView();
}
function handleLockedViewPreparedClick(event){
  if(!newViewHeaderLocked||!lockedViewStateCache)return;
  const target=event.target&&event.target.closest?event.target:null;
  if(!target)return;
  const unlock=target.closest('.new-view-lock-toggle');
  if(unlock){
    event.preventDefault();event.stopImmediatePropagation();
    endLockedViewPreparedMode();
    return;
  }
  const filter=target.closest('.view-filter-toggle');
  if(filter){
    event.preventDefault();event.stopImmediatePropagation();
    const modes=lockedViewFilterOrder.length?lockedViewFilterOrder:getLockedViewFilterOrder();
    const current=modes.indexOf(String(weaponFilterMode||''));
    const next=modes[(current<0?0:current+1)%modes.length];
    showLockedViewPreparedState(activeUnitIndex,next);
    return;
  }
  const unit=target.closest('.view-unit-row[data-roster-index]');
  if(unit){
    event.preventDefault();event.stopImmediatePropagation();
    const index=Number(unit.dataset.rosterIndex);
    const next=activeUnitIndex===index?null:index;
    showLockedViewPreparedState(next,weaponFilterMode);
    return;
  }
  // Everything else in locked VIEW is inert, including Probable, navigation,
  // version actions, Waha, edits, and any control that could start processing.
  event.preventDefault();
  event.stopImmediatePropagation();
}
document.addEventListener('click',handleLockedViewPreparedClick,true);
'''
view_np = view_np.replace(helper_marker, lock_helpers + '\n' + helper_marker, 1)

# Use the existing lock button; do not add or move UI.
old_lock_click = "lb.onclick=()=>{if(newViewHeaderLocked){newViewHeaderLocked=false;frozenNewViewSnapshot=null;syncNewViewLockButton(lb);requestAnimationFrame(refreshNewView);return}const snapshot=captureNewViewSnapshot();frozenNewViewSnapshot=snapshot;activateNewViewSnapshot(snapshot);newViewHeaderLocked=true;syncNewViewLockButton(lb)}"
new_lock_click = "lb.onclick=()=>{if(newViewHeaderLocked){endLockedViewPreparedMode();return}beginLockedViewPreparedMode()}"
if view_np.count(old_lock_click) != 1:
    raise SystemExit(f'New View lock click handler: expected 1 match, found {view_np.count(old_lock_click)}')
view_np = view_np.replace(old_lock_click, new_lock_click, 1)

# renderFrozenNewView may still be reached by old internal paths. Once prepared
# DOM exists it must only select the already-built state, never rebuild rows.
old_frozen = r'''function renderFrozenNewView(){
  if(!newViewProcessingLocked()||!frozenNewViewSnapshot)return false;
  applyNewViewHeaderSnapshot(frozenNewViewSnapshot.header);
  const rows=cloneNewViewValue(frozenNewViewSnapshot.rows);
  return renderNewViewRosterRows(Array.isArray(rows)?rows:[]);
}'''
new_frozen = r'''function renderFrozenNewView(){
  if(!newViewProcessingLocked()||!frozenNewViewSnapshot)return false;
  if(lockedViewStateCache)return showLockedViewPreparedState(activeUnitIndex,weaponFilterMode);
  applyNewViewHeaderSnapshot(frozenNewViewSnapshot.header);
  const rows=cloneNewViewValue(frozenNewViewSnapshot.rows);
  return renderNewViewRosterRows(Array.isArray(rows)?rows:[]);
}'''
if view_np.count(old_frozen) != 1:
    raise SystemExit(f'New View frozen renderer: expected 1 match, found {view_np.count(old_frozen)}')
view_np = view_np.replace(old_frozen, new_frozen, 1)

# A locked VIEW cannot switch mode or clear/rebuild content. Re-showing VIEW only
# selects a prepared state and returns before persistent-grid/content work.
old_render_start = "function renderPage(p){\n  activePageMode=p;"
new_render_start = "function renderPage(p){\n  if(newViewHeaderLocked&&lockedViewStateCache){if(p!=='view')return false;return showLockedViewPreparedState(activeUnitIndex,weaponFilterMode)}\n  activePageMode=p;"
if view_np.count(old_render_start) != 1:
    raise SystemExit(f'New View renderPage start: expected 1 match, found {view_np.count(old_render_start)}')
view_np = view_np.replace(old_render_start, new_render_start, 1)

# Write unified iframe back.
text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.103
    Scope: Complete the next New View lock optimization on the current V31.102 unified-page baseline. Pressing the existing Lock now pre-renders every current Unit x weapon-filter combination once, before the lock state turns on, using the already-detached V31.93 snapshot. Those prepared DOM states are retained in memory. While locked, Unit open/close and the existing filter carousel only switch which prepared state is visible; they do not call applyActiveUnitDetails, syncUnitDetailVisibility, renderNewViewRosterRows, parent/model bridges, persistence, or animation-frame refreshes. All other locked View controls are inert, including any Probable control; Probable-looking controls are also visually disabled in prepared states. The live original View DOM remains mounted but hidden so Unlock can turn the lock off, discard the prepared states, and perform exactly one normal fresh synchronization. No UI control was added or moved.
    Risk areas: New View locked-mode DOM/state handling only. Unlocked View behavior, unified Edit, current Boyz point-option behavior, persistent 40x16 grid fast path, compact Weapon Tags, Version/Update/Download, Old Edit, Cards, CSV data, Waha routing, and normal Probable behavior remain unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.102\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

# Retain only the five newest detailed V31 notes.
notes = list(re.finditer(r'\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n', text, re.S))
for note_match in reversed(notes[5:]):
    text = text[:note_match.start()] + text[note_match.end():]

# Final acceptance checks.
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing after writeback')
final_view = html.unescape(vm.group(2))
required_view = [
    'let lockedViewStateCache=null;',
    'let lockedViewStateLayers=[];',
    'function buildLockedViewPreparedDom()',
    'function showLockedViewPreparedState(unitIndex,mode)',
    'function beginLockedViewPreparedMode()',
    'function endLockedViewPreparedMode()',
    'function handleLockedViewPreparedClick(event)',
    "document.addEventListener('click',handleLockedViewPreparedClick,true);",
    "layer.className='new-view-locked-state';",
    "lockedViewFilterOrder=getLockedViewFilterOrder();",
    "renderLockedViewCombination(unitIndex,mode);",
    "applyActiveUnitDetails();",
    "syncUnitDetailVisibility();",
    "newViewHeaderLocked=true;",
    "lb.onclick=()=>{if(newViewHeaderLocked){endLockedViewPreparedMode();return}beginLockedViewPreparedMode()}",
    "if(lockedViewStateCache)return showLockedViewPreparedState(activeUnitIndex,weaponFilterMode);",
    "if(newViewHeaderLocked&&lockedViewStateCache){if(p!=='view')return false;return showLockedViewPreparedState(activeUnitIndex,weaponFilterMode)}",
    '.new-view-lock-original-hidden{display:none!important}',
    '.new-view-locked-state{display:contents}',
    '.new-view-lock-disabled{opacity:.45!important;pointer-events:none!important}',
]
for value in required_view:
    if value not in final_view:
        raise SystemExit('V31.103 New View acceptance failed: ' + value)

# Locked click/show paths must remain display-only: no rendering/model/persistence.
for fn_name in ['showLockedViewPreparedState', 'handleLockedViewPreparedClick']:
    match = re.search(r'function '+fn_name+r'\([^)]*\)\{(.*?)\n\}', final_view, re.S)
    if not match:
        raise SystemExit('V31.103 locked helper verification missing: ' + fn_name)
    body = match.group(1)
    for forbidden in ['applyActiveUnitDetails(', 'syncUnitDetailVisibility(', 'renderNewViewRosterRows(', 'parent.', 'requestAnimationFrame(', 'localStorage', 'save']:
        if forbidden in body:
            raise SystemExit(f'V31.103 locked {fn_name} contains processing call: {forbidden}')

# The expensive renderer calls are permitted only in preparation before lock.
begin_match = re.search(r'function beginLockedViewPreparedMode\(\)\{(.*?)\n\}', final_view, re.S)
if not begin_match:
    raise SystemExit('V31.103 begin-lock verification missing')
begin_body = begin_match.group(1)
if begin_body.find('buildLockedViewPreparedDom()') > begin_body.find('newViewHeaderLocked=true;'):
    raise SystemExit('V31.103 lock flips on before prepared DOM is built')

required_outer = [
    '<title>WH40k 11th V31.103</title>',
    'The current baseline is WH40k_11th_V31.103;',
    'const APP_VERSION = "31.103";',
    "version: 'V31.103',",
    'CHANGE NOTE - WH40k_11th_V31.103',
]
for value in required_outer:
    if value not in text:
        raise SystemExit('V31.103 release acceptance failed: ' + value)

# Protect the current V31.100-V31.102 architecture and styling.
for required in [
    'function ensurePersistentGridCells()',
    'function clearModeContent()',
    'function renderCachedView()',
    'function renderCachedEdit()',
    '.weapon-tag{height:var(--std);flex:0 0 auto;padding:0 8px;border:1px solid var(--btnborder);',
    "const pointLabel=String(data&&data.pointLabel||'').trim();",
]:
    if required not in final_view:
        raise SystemExit('V31.103 regressed current unified-page contract: ' + required)
for forbidden in ['id="newEditPageScreen"', 'id="npEditFrame"', 'parent.getNewEdit']:
    if forbidden in text:
        raise SystemExit('V31.103 regressed retired standalone New Edit: ' + forbidden)

path.write_text(text, encoding='utf-8')
print('Built V31.103: locked View uses prebuilt Unit/filter DOM states only')
