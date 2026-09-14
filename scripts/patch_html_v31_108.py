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


# Sequential release metadata. Rebase on the current V31.107 detail-row baseline.
once('<title>WH40k 11th V31.107</title>', '<title>WH40k 11th V31.108</title>', 'title')
once('The current baseline is WH40k_11th_V31.107;', 'The current baseline is WH40k_11th_V31.108;', 'baseline')
once('const APP_VERSION = "31.107";', 'const APP_VERSION = "31.108";', 'APP_VERSION')
once("version: 'V31.107',", "version: 'V31.108',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing')
view_np = html.unescape(vm.group(2))

# Protect current New View contracts before changing only frame-height behavior.
for required in [
    'function syncExpandedLayout(expansionRows){',
    'function positionNewViewVersionControls()',
    'function cloneLockedViewState(unitIndex,mode)',
    'function showLockedViewPreparedState(unitIndex,mode)',
    'function suspendNewViewBackgroundWork()',
    'function resumeNewViewBackgroundWork()',
    'window.getNewViewLockDiagnostics=getNewViewLockDiagnostics;',
    'function ensurePersistentGridCells()',
    'function clearModeContent()',
]:
    if required not in view_np:
        raise SystemExit('V31.108 baseline contract missing: ' + required)

# Expanded Unit/detail rows already create real implicit rows in the inner grid,
# but an iframe does not automatically grow with its document. Keep a 40-row
# minimum and resize the outer frame to the actual sheet height.
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

frame_helpers = r'''const NEW_VIEW_BASE_GRID_ROWS=40;
function getNewViewFrameHeight(){
  const rawCell=getComputedStyle(document.documentElement).getPropertyValue('--cell');
  const cellSize=parseFloat(rawCell)||26;
  const baseHeight=Math.ceil(NEW_VIEW_BASE_GRID_ROWS*cellSize);
  const gridHeight=Math.ceil(grid.getBoundingClientRect().height);
  return Math.max(baseHeight,gridHeight);
}
function applyNewViewFrameHeight(height){
  if(!frameElement)return 0;
  const measured=Math.ceil(Number(height)||getNewViewFrameHeight());
  const nextHeight=Math.max(1,measured);
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

# Version controls move after the last Unit. Measure again after their row is set
# so an expanded roster cannot leave those controls below the iframe boundary.
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

# Prepared Lock states do not run live layout when switching. Save the measured
# height with each state and restore it with the same display-only state switch.
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

# Version history adds/removes up to two rows; keep the frame aligned there too.
history_tail = '''    grid.appendChild(b);
  });
}
async function toggleNewViewVersionHistory(){'''
history_tail_new = '''    grid.appendChild(b);
  });
  syncNewViewFrameHeight();
}
async function toggleNewViewVersionHistory(){'''
if view_np.count(history_tail) != 1:
    raise SystemExit(f'version-history tail: expected 1 match, found {view_np.count(history_tail)}')
view_np = view_np.replace(history_tail, history_tail_new, 1)

# Write unified iframe back.
text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.108
    Scope: Fix New View mobile scrolling when a Unit is expanded. The embedded New View iframe now follows the actual sheet height instead of remaining fixed while detail/Weapon rows extend below it. The frame keeps a 40-row minimum, grows when expanded content or Version rows move lower, and shrinks when content collapses. Locked prepared View states store their required frame height during preparation and restore it during the existing display-only state switch. No touch handlers, scroll interception, UI controls, or visual styling are added.
    Risk areas: New View iframe height synchronization only. V31.107 Unit Detail sizing, V31.106 locked-background suspension, prepared locked states, VIEW/EDIT controls, shared Grid Mode, roster rendering, unified Edit, Version/Update/Download behavior, Old Edit, Cards, persistence, CSV data, Waha routing, and Probable remain unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.107\n'
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
    'const NEW_VIEW_BASE_GRID_ROWS=40;',
    'function getNewViewFrameHeight()',
    'function applyNewViewFrameHeight(height)',
    'function syncNewViewFrameHeight()',
    "const gridHeight=Math.ceil(grid.getBoundingClientRect().height);",
    "if(frameElement.style.height!==cssHeight)frameElement.style.height=cssHeight;",
    'layer.dataset.frameHeight=String(getNewViewFrameHeight());',
    'applyNewViewFrameHeight(Number(target.dataset.frameHeight)||0);',
    'function suspendNewViewBackgroundWork()',
    'function resumeNewViewBackgroundWork()',
    'window.getNewViewLockDiagnostics=getNewViewLockDiagnostics;',
    'function ensurePersistentGridCells()',
    'function clearModeContent()',
    'justify-content:flex-start;',
]:
    if required not in final_view:
        raise SystemExit('V31.108 New View acceptance failed: ' + required)

for forbidden in ["addEventListener('touchmove'", 'ontouchmove=']:
    if forbidden in final_view:
        raise SystemExit('V31.108 unexpected touch-scroll interception: ' + forbidden)

for required in [
    '<title>WH40k 11th V31.108</title>',
    'The current baseline is WH40k_11th_V31.108;',
    'const APP_VERSION = "31.108";',
    "version: 'V31.108',",
    'CHANGE NOTE - WH40k_11th_V31.108',
]:
    if required not in text:
        raise SystemExit('V31.108 acceptance failed: ' + required)

path.write_text(text, encoding='utf-8')
print('Built V31.108: dynamic New View iframe height for expanded-unit scrolling')
