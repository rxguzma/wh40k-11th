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


# Sequential release metadata. This patch is intentionally based on the current
# V31.105 unified View/Edit baseline so the corrected mode/grid controls survive.
once('<title>WH40k 11th V31.105</title>', '<title>WH40k 11th V31.106</title>', 'title')
once('The current baseline is WH40k_11th_V31.105;', 'The current baseline is WH40k_11th_V31.106;', 'baseline')
once('const APP_VERSION = "31.105";', 'const APP_VERSION = "31.106";', 'APP_VERSION')
once("version: 'V31.105',", "version: 'V31.106',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing')
view_np = html.unescape(vm.group(2))

# Protect the current lock/prepared-state and V31.105 control contracts before
# changing background behavior.
for required in [
    'function beginLockedViewPreparedMode()',
    'function endLockedViewPreparedMode()',
    'function showLockedViewPreparedState(unitIndex,mode)',
    'let newViewVersionObserver=null;',
    'function ensureNewViewVersionObserver()',
    'function positionNewViewVersionControls()',
    'function refreshNewView()',
    'function ensurePersistentGridCells()',
    "toggle.textContent=p==='view'?'VIEW':'EDIT';",
    "gb.classList.toggle('active-green',gridOn);",
]:
    if required not in view_np:
        raise SystemExit('V31.106 baseline contract missing: ' + required)

# Track/cancel the only New View background observer and the two View RAF paths
# that can otherwise remain queued across the lock transition. Counters increase
# only when live work actually runs, allowing a locked baseline comparison.
old_observer_state = 'let newViewVersionObserver=null;'
new_observer_state = '''let newViewVersionObserver=null;
let newViewVersionObserverActive=false;
let newViewVersionRafId=0;
let newViewRefreshRafId=0;
let newViewLockCounterBaseline=null;
const newViewBackgroundCounters={observerCallbacks:0,versionLayoutPasses:0,liveRefreshes:0};'''
once(old_observer_state, new_observer_state, 'New View background state')

# Any direct version-layout call must become a no-op once VIEW is locked.
position_sig = 'function positionNewViewVersionControls(){'
position_new = "function positionNewViewVersionControls(){if(newViewProcessingLocked())return 0;newViewBackgroundCounters.versionLayoutPasses++;"
once(position_sig, position_new, 'version position gate/counter')

# Replace the always-connected MutationObserver with an explicitly suspendable
# observer. Disconnecting at Lock also discards queued mutation notifications.
old_observer = r'''function ensureNewViewVersionObserver(){
  if(newViewVersionObserver)return;
  newViewVersionObserver=new MutationObserver(mutations=>{
    if(mutations.some(newViewVersionMutationTouchesLayout))positionNewViewVersionControls();
  });
  newViewVersionObserver.observe(grid,{childList:true,subtree:true,attributes:true,attributeFilter:['style']});
}'''
new_observer = r'''function ensureNewViewVersionObserver(){
  if(newViewProcessingLocked())return false;
  if(!newViewVersionObserver){
    newViewVersionObserver=new MutationObserver(mutations=>{
      if(newViewProcessingLocked())return;
      newViewBackgroundCounters.observerCallbacks++;
      if(mutations.some(newViewVersionMutationTouchesLayout))positionNewViewVersionControls();
    });
  }
  if(!newViewVersionObserverActive){
    newViewVersionObserver.observe(grid,{childList:true,subtree:true,attributes:true,attributeFilter:['style']});
    newViewVersionObserverActive=true;
  }
  return true;
}
function scheduleNewViewVersionPosition(){
  if(newViewProcessingLocked())return false;
  if(newViewVersionRafId)cancelAnimationFrame(newViewVersionRafId);
  newViewVersionRafId=requestAnimationFrame(()=>{
    newViewVersionRafId=0;
    if(newViewProcessingLocked())return;
    positionNewViewVersionControls();
  });
  return true;
}
function scheduleNewViewRefresh(){
  if(newViewProcessingLocked())return false;
  if(newViewRefreshRafId)cancelAnimationFrame(newViewRefreshRafId);
  newViewRefreshRafId=requestAnimationFrame(()=>{
    newViewRefreshRafId=0;
    if(newViewProcessingLocked())return;
    refreshNewView();
  });
  return true;
}
function suspendNewViewBackgroundWork(){
  if(newViewVersionObserver&&newViewVersionObserverActive){
    newViewVersionObserver.disconnect();
    newViewVersionObserverActive=false;
  }
  if(newViewVersionRafId){cancelAnimationFrame(newViewVersionRafId);newViewVersionRafId=0;}
  if(newViewRefreshRafId){cancelAnimationFrame(newViewRefreshRafId);newViewRefreshRafId=0;}
  return true;
}
function resumeNewViewBackgroundWork(){
  if(newViewProcessingLocked())return false;
  ensureNewViewVersionObserver();
  scheduleNewViewVersionPosition();
  return true;
}
function getNewViewLockDiagnostics(){
  const counters=Object.assign({},newViewBackgroundCounters);
  const baseline=newViewLockCounterBaseline?Object.assign({},newViewLockCounterBaseline):null;
  const unchanged=Boolean(newViewProcessingLocked()&&baseline)&&Object.keys(counters).every(key=>counters[key]===baseline[key]);
  return {
    locked:newViewProcessingLocked(),
    observerActive:newViewVersionObserverActive,
    versionRafPending:Boolean(newViewVersionRafId),
    refreshRafPending:Boolean(newViewRefreshRafId),
    counters,
    baseline,
    unchangedWhileLocked:unchanged
  };
}
window.getNewViewLockDiagnostics=getNewViewLockDiagnostics;'''
if view_np.count(old_observer) != 1:
    raise SystemExit(f'New View version observer block: expected 1 match, found {view_np.count(old_observer)}')
view_np = view_np.replace(old_observer, new_observer, 1)

# Version/history continuations can finish asynchronously after the user locks.
# Their UI continuation must stop immediately once locked.
for old, new, label in [
    ('function renderNewViewVersionHistory(){', 'function renderNewViewVersionHistory(){if(newViewProcessingLocked())return;', 'version history render gate'),
    ('async function toggleNewViewVersionHistory(){', 'async function toggleNewViewVersionHistory(){if(newViewProcessingLocked())return;', 'version history async gate'),
]:
    once(old, new, label)

# The version controls used to leave an untracked RAF queued. Route it through
# the cancellable scheduler instead.
once('requestAnimationFrame(positionNewViewVersionControls);', 'scheduleNewViewVersionPosition();', 'version position RAF scheduler')

# Count only actual live VIEW synchronizations, after the existing lock gate.
old_refresh = 'function refreshNewView(){if(newViewProcessingLocked())return false;refreshNewViewTitleFromLegacy();return refreshAlternateViewUnitsFromParent()}'
new_refresh = 'function refreshNewView(){if(newViewProcessingLocked())return false;newViewBackgroundCounters.liveRefreshes++;refreshNewViewTitleFromLegacy();return refreshAlternateViewUnitsFromParent()}'
once(old_refresh, new_refresh, 'live View refresh counter')

# Initial/fallback VIEW refresh is now cancellable if Lock is pressed before its
# animation frame fires. EDIT RAF behavior remains unchanged.
old_view_raf = 'else if(!renderCachedView())requestAnimationFrame(refreshNewView)'
new_view_raf = 'else if(!renderCachedView())scheduleNewViewRefresh()'
once(old_view_raf, new_view_raf, 'View fallback refresh scheduler')

# Lock preparation may create many DOM mutations. Disconnect/cancel all New View
# background work BEFORE the lock flag turns on, so queued observer notifications
# and RAF callbacks cannot execute afterward. Take the diagnostics baseline only
# after preparation and suspension are complete.
old_lock_finish = '''  // Lock becomes true only after every prepared state is built and mounted.
  newViewHeaderLocked=true;
  return true;'''
new_lock_finish = '''  // Lock becomes true only after every prepared state is built and mounted.
  suspendNewViewBackgroundWork();
  newViewLockCounterBaseline=Object.assign({},newViewBackgroundCounters);
  newViewHeaderLocked=true;
  return true;'''
once(old_lock_finish, new_lock_finish, 'Lock background suspension')

# Unlock first, discard prepared state, perform exactly one fresh live sync while
# the observer is still suspended, then resume the observer and one version-row
# position RAF. This avoids observer churn during the live roster rebuild.
old_unlock = r'''function endLockedViewPreparedMode(){
  if(!newViewHeaderLocked)return false;
  // Unlock first, then discard prepared state and perform one fresh live sync.
  newViewHeaderLocked=false;
  clearLockedViewPreparedDom();
  frozenNewViewSnapshot=null;
  const lockButton=grid.querySelector('.new-view-lock-toggle');
  if(lockButton)syncNewViewLockButton(lockButton);
  return refreshNewView();
}'''
new_unlock = r'''function endLockedViewPreparedMode(){
  if(!newViewHeaderLocked)return false;
  // Unlock first, then discard prepared state and perform one fresh live sync.
  newViewHeaderLocked=false;
  clearLockedViewPreparedDom();
  frozenNewViewSnapshot=null;
  const lockButton=grid.querySelector('.new-view-lock-toggle');
  if(lockButton)syncNewViewLockButton(lockButton);
  const ok=refreshNewView();
  newViewLockCounterBaseline=null;
  resumeNewViewBackgroundWork();
  return ok;
}'''
if view_np.count(old_unlock) != 1:
    raise SystemExit(f'New View unlock block: expected 1 match, found {view_np.count(old_unlock)}')
view_np = view_np.replace(old_unlock, new_unlock, 1)

# Write unified iframe back.
text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.106
    Scope: Suspend remaining New View background processing while the existing Lock is on, rebased on the current V31.105 unified View/Edit baseline. The Version layout MutationObserver is now explicitly disconnected before Lock becomes active and reattached only after Unlock's one live roster/header synchronization. Pending Version-position and initial/fallback View-refresh animation frames are tracked and cancelled on Lock. Version/history async UI continuations and direct version-position calls return immediately if View is locked. Internal diagnostics expose observer/RAF state plus three live-work counters; their baseline is captured after lock preparation so unchangedWhileLocked remains true only when observer callbacks, version layout passes, and live refreshes stay at zero movement during the locked period. Unlock keeps the observer suspended during its single fresh synchronization, then resumes the observer and schedules one version-control position pass. No UI controls are added or moved.
    Risk areas: New View background observer/RAF lifecycle and internal diagnostics only. V31.103 prepared locked states, V31.105 VIEW/EDIT and shared Grid Mode controls, unlocked View behavior, unified Edit, Boyz point options, compact Weapon Tags, Version/Update/Download actions, Old Edit, Cards, persistence, CSV data, Waha routing, and normal Probable behavior remain unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.105\n'
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
    'let newViewVersionObserverActive=false;',
    'let newViewVersionRafId=0;',
    'let newViewRefreshRafId=0;',
    'const newViewBackgroundCounters={observerCallbacks:0,versionLayoutPasses:0,liveRefreshes:0};',
    'function suspendNewViewBackgroundWork()',
    'function resumeNewViewBackgroundWork()',
    'function scheduleNewViewVersionPosition()',
    'function scheduleNewViewRefresh()',
    'function getNewViewLockDiagnostics()',
    'window.getNewViewLockDiagnostics=getNewViewLockDiagnostics;',
    'newViewVersionObserver.disconnect();',
    'cancelAnimationFrame(newViewVersionRafId)',
    'cancelAnimationFrame(newViewRefreshRafId)',
    'suspendNewViewBackgroundWork();',
    'newViewLockCounterBaseline=Object.assign({},newViewBackgroundCounters);',
    'const ok=refreshNewView();',
    'resumeNewViewBackgroundWork();',
    "function positionNewViewVersionControls(){if(newViewProcessingLocked())return 0;newViewBackgroundCounters.versionLayoutPasses++;",
    'function renderNewViewVersionHistory(){if(newViewProcessingLocked())return;',
    'async function toggleNewViewVersionHistory(){if(newViewProcessingLocked())return;',
    'else if(!renderCachedView())scheduleNewViewRefresh()',
    'scheduleNewViewVersionPosition();',
    "toggle.textContent=p==='view'?'VIEW':'EDIT';",
    "gb.classList.toggle('active-green',gridOn);",
    'function buildLockedViewPreparedDom()',
    'function showLockedViewPreparedState(unitIndex,mode)',
]
for value in required_view:
    if value not in final_view:
        raise SystemExit('V31.106 acceptance failed: ' + value)

for forbidden in [
    'requestAnimationFrame(positionNewViewVersionControls);',
    'else if(!renderCachedView())requestAnimationFrame(refreshNewView)',
]:
    if forbidden in final_view:
        raise SystemExit('V31.106 untracked locked-capable background path remains: ' + forbidden)

# Audit recurring/background primitives inside the unified iframe. MutationObserver
# is expected exactly once and is the observer now suspended by the lock. There
# should be no timer/idle/resize observer loop hiding elsewhere in New View.
audit_counts = {
    'MutationObserver': final_view.count('new MutationObserver('),
    'ResizeObserver': final_view.count('new ResizeObserver('),
    'setInterval': final_view.count('setInterval('),
    'setTimeout': final_view.count('setTimeout('),
    'requestIdleCallback': final_view.count('requestIdleCallback('),
}
print('V31.106 New View background audit:', audit_counts)
if audit_counts['MutationObserver'] != 1:
    raise SystemExit(f"V31.106 expected exactly one MutationObserver, found {audit_counts['MutationObserver']}")
for primitive in ['ResizeObserver','setInterval','setTimeout','requestIdleCallback']:
    if audit_counts[primitive]:
        raise SystemExit(f'V31.106 unhandled New View background primitive remains: {primitive} x{audit_counts[primitive]}')

required_outer = [
    '<title>WH40k 11th V31.106</title>',
    'The current baseline is WH40k_11th_V31.106;',
    'const APP_VERSION = "31.106";',
    "version: 'V31.106',",
    'CHANGE NOTE - WH40k_11th_V31.106',
]
for value in required_outer:
    if value not in text:
        raise SystemExit('V31.106 release acceptance failed: ' + value)

path.write_text(text, encoding='utf-8')
print('Built V31.106: locked View suspends observer/RAF background processing')
