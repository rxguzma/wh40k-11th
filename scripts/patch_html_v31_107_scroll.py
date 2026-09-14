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


# Sequential release metadata. Main is still V31.106; the other attempted
# V31.107 build failed before changing the HTML.
once('<title>WH40k 11th V31.106</title>', '<title>WH40k 11th V31.107</title>', 'title')
once('The current baseline is WH40k_11th_V31.106;', 'The current baseline is WH40k_11th_V31.107;', 'baseline')
once('const APP_VERSION = "31.106";', 'const APP_VERSION = "31.107";', 'APP_VERSION')
once("version: 'V31.106',", "version: 'V31.107',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing')
view_np = html.unescape(vm.group(2))

# Protect the V31.106 lock/background contracts. This patch changes only the
# iframe height that contains New View.
for required in [
    'function syncExpandedLayout(expansionRows){',
    'function positionNewViewVersionControls()',
    'function cloneLockedViewState(unitIndex,mode)',
    'function showLockedViewPreparedState(unitIndex,mode)',
    'function suspendNewViewBackgroundWork()',
    'function resumeNewViewBackgroundWork()',
    'window.getNewViewLockDiagnostics=getNewViewLockDiagnostics;',
    'function ensurePersistentGridCells()',
]:
    if required not in view_np:
        raise SystemExit('V31.107 baseline contract missing: ' + required)

# Preserve the exact current collapsed frame height, whatever CSS currently
# supplies it. Expanded grid rows can then grow the iframe without introducing a
# nested mobile scroll surface; collapsing returns to the original frame height.
layout_start = view_np.find('function syncExpandedLayout(expansionRows){')
layout_end = view_np.find('function applyActiveUnitDetails(){', layout_start)
if layout_start < 0 or layout_end < 0:
    raise SystemExit('New View expanded-layout bounds missing')
layout_block = view_np[layout_start:layout_end]
layout_tail = """  grid.querySelectorAll('.grid-cell').forEach(cell=>{
    const row=parseInt(cell.style.gridRow||'',10);
    cell.hidden=Number.isFinite(row)&&row>activeGridRows;
  });
}"""
if layout_block.count(layout_tail) != 1:
    raise SystemExit(f'expanded-layout tail: expected 1 match, found {layout_block.count(layout_tail)}')

frame_helpers = r'''const NEW_VIEW_BASE_FRAME_HEIGHT=frameElement?Math.ceil(frameElement.getBoundingClientRect().height):806;
function getNewViewFrameHeight(){
  const gridHeight=Math.ceil(Math.max(grid.getBoundingClientRect().height,grid.scrollHeight||0));
  return Math.max(NEW_VIEW_BASE_FRAME_HEIGHT,gridHeight);
}
function applyNewViewFrameHeight(height){
  if(!frameElement)return 0;
  const measured=Math.ceil(Number(height)||getNewViewFrameHeight());
  const nextHeight=Math.max(NEW_VIEW_BASE_FRAME_HEIGHT,measured);
  const cssHeight=String(nextHeight)+'px';
  if(frameElement.style.height!==cssHeight)frameElement.style.height=cssHeight;
  return nextHeight;
}
function syncNewViewFrameHeight(){
  return applyNewViewFrameHeight(getNewViewFrameHeight());
}
'''
new_layout_tail = """  grid.querySelectorAll('.grid-cell').forEach(cell=>{
    const row=parseInt(cell.style.gridRow||'',10);
    cell.hidden=Number.isFinite(row)&&row>activeGridRows;
  });
  syncNewViewFrameHeight();
}"""
layout_block = layout_block.replace(layout_tail, new_layout_tail, 1)
view_np = view_np[:layout_start] + frame_helpers + layout_block + view_np[layout_end:]

# Version controls are positioned below the roster, so include their final row in
# the frame measurement after each layout pass.
version_return = '''  return versionRow;
}
function newViewVersionMutationTouchesLayout'''
version_return_new = '''  syncNewViewFrameHeight();
  return versionRow;
}
function newViewVersionMutationTouchesLayout'''
if view_np.count(version_return) != 1:
    raise SystemExit(f'version-position return: expected 1 match, found {view_np.count(version_return)}')
view_np = view_np.replace(version_return, version_return_new, 1)

# Locked View uses prebuilt DOM states and intentionally performs no live layout.
# Capture the already-computed frame height with each prepared state, then restore
# it using only one iframe style assignment when the prepared state is shown.
clone_tail = '''  primeLockedViewLayer(layer);
  return layer;
}'''
clone_tail_new = '''  primeLockedViewLayer(layer);
  layer.dataset.frameHeight=String(getNewViewFrameHeight());
  return layer;
}'''
if view_np.count(clone_tail) != 1:
    raise SystemExit(f'locked-state clone tail: expected 1 match, found {view_np.count(clone_tail)}')
view_np = view_np.replace(clone_tail, clone_tail_new, 1)

show_tail = '''  activeUnitIndex=unitIndex;
  weaponFilterMode=mode;
  selectedWeaponIndex=null;
  return true;
}
function beginLockedViewPreparedMode(){'''
show_tail_new = '''  activeUnitIndex=unitIndex;
  weaponFilterMode=mode;
  selectedWeaponIndex=null;
  applyNewViewFrameHeight(Number(target.dataset.frameHeight)||0);
  return true;
}
function beginLockedViewPreparedMode(){'''
if view_np.count(show_tail) != 1:
    raise SystemExit(f'locked-state show tail: expected 1 match, found {view_np.count(show_tail)}')
view_np = view_np.replace(show_tail, show_tail_new, 1)

# Write the unified iframe back.
text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.107
    Scope: Fix New View mobile scrolling when a Unit is expanded. New View now preserves its existing collapsed iframe height but dynamically grows the iframe to the actual sheet height when Unit detail/Weapon rows push the grid lower, then shrinks back on collapse. Version-row positioning is included in the measurement. Prepared locked View states store and restore their required iframe height using the existing display-only state switch. No touch handlers, scroll interception, new UI controls, or visual styling are added.
    Risk areas: New View iframe height synchronization only. V31.106 locked-background suspension, prepared locked states, VIEW/EDIT controls, shared Grid Mode, roster rendering, unified Edit, Version/Update/Download behavior, Old Edit, Cards, persistence, CSV data, Waha routing, and Probable remain unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.106\n'
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
for required in [
    'const NEW_VIEW_BASE_FRAME_HEIGHT=frameElement?Math.ceil(frameElement.getBoundingClientRect().height):806;',
    'function getNewViewFrameHeight()',
    'function applyNewViewFrameHeight(height)',
    'function syncNewViewFrameHeight()',
    'grid.scrollHeight||0',
    'layer.dataset.frameHeight=String(getNewViewFrameHeight());',
    'applyNewViewFrameHeight(Number(target.dataset.frameHeight)||0);',
    'function suspendNewViewBackgroundWork()',
    'function resumeNewViewBackgroundWork()',
    'window.getNewViewLockDiagnostics=getNewViewLockDiagnostics;',
    'function ensurePersistentGridCells()',
]:
    if required not in final_view:
        raise SystemExit('V31.107 New View acceptance failed: ' + required)

for forbidden in ["addEventListener('touchmove'", 'ontouchmove=']:
    if forbidden in final_view:
        raise SystemExit('V31.107 unexpected touch-scroll interception: ' + forbidden)

for required in [
    '<title>WH40k 11th V31.107</title>',
    'The current baseline is WH40k_11th_V31.107;',
    'const APP_VERSION = "31.107";',
    "version: 'V31.107',",
    'CHANGE NOTE - WH40k_11th_V31.107',
]:
    if required not in text:
        raise SystemExit('V31.107 acceptance failed: ' + required)

path.write_text(text, encoding='utf-8')
print('Built V31.107: dynamic New View iframe height for expanded-unit scrolling')
