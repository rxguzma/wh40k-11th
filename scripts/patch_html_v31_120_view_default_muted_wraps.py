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
once('<title>WH40k 11th V31.119</title>', '<title>WH40k 11th V31.120</title>', 'title')
once('The current baseline is WH40k_11th_V31.119;', 'The current baseline is WH40k_11th_V31.120;', 'baseline')
once('const APP_VERSION = "31.119";', 'const APP_VERSION = "31.120";', 'APP_VERSION')
once("version: 'V31.119',", "version: 'V31.120',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing')
view_np = html.unescape(vm.group(2))

# Preserve the established View selection classes/colors. This pass only changes
# their default state and adds non-layout overlay borders.
for required in [
    'let activeUnitIndex=null;',
    'let selectedWeaponIndex=null;',
    "function syncWeaponLayout(){",
    "function syncUnitDetailVisibility(){",
    "function refreshBoyzNewViewSelection(){",
    ".weapon-row.weapon-muted .weapon-name,.weapon-row.weapon-muted .weapon-stat{opacity:.5}",
    ".weapon-row.weapon-active .weapon-name,.weapon-row.weapon-active .weapon-stat{color:#80d6a3;opacity:1}",
    ".weapon-tags.weapon-muted .weapon-tag{color:var(--muted)}",
    ".view-unit-row.unit-active .view-unit-name{color:#80d6a3!important}",
]:
    if required not in view_np:
        raise SystemExit('V31.120 baseline contract missing: ' + required)

# Default View presentation: roster content is muted until selected. Open Unit
# keeps the existing active color and additionally renders its name in CAPS.
style_marker = '</style>'
view_css = r'''
/* V31.120 View default-selection presentation. Uses existing muted/active colors only. */
.view-stat-header .view-stat-label{opacity:.5}
.view-unit-row:not(.unit-active) .view-unit-name,.view-unit-row:not(.unit-active) .view-unit-stat{opacity:.5}
.view-unit-row.unit-active .view-unit-name{text-transform:uppercase}
.weapon-header{opacity:.5}
.detail-box-row .detail-box{opacity:.5}
.draft-grid{position:relative}
.view-open-unit-wrap,.view-selected-weapon-wrap{position:absolute;box-sizing:border-box;border:1px solid var(--border);border-radius:0;background:transparent;pointer-events:none;z-index:8}
.view-selected-weapon-wrap{z-index:9}
'''
if view_css.strip() in view_np:
    raise SystemExit('V31.120 View CSS already present')
if view_np.count(style_marker) < 1:
    raise SystemExit('Unified View style close marker missing')
view_np = view_np.replace(style_marker, view_css + style_marker, 1)

# Existing normal weapon selection currently mutes only after a weapon is chosen.
# Change that one state rule so every visible weapon starts muted and only the
# selected weapon becomes active/unmuted.
old_normal_muted = 'const muted=hasSelection&&!active;'
new_normal_muted = 'const muted=!active;'
if view_np.count(old_normal_muted) != 1:
    raise SystemExit(f'normal weapon muted state: expected 1 match, found {view_np.count(old_normal_muted)}')
view_np = view_np.replace(old_normal_muted, new_normal_muted, 1)

# Boyz has its own dynamic sub-unit weapon renderer. Apply the same default-muted
# rule without changing the existing sub-unit focus behavior.
old_boyz_muted = 'const muted=Boolean(selected)&&!active;'
new_boyz_muted = 'const muted=!active;'
if view_np.count(old_boyz_muted) != 1:
    raise SystemExit(f'Boyz weapon muted state: expected 1 match, found {view_np.count(old_boyz_muted)}')
view_np = view_np.replace(old_boyz_muted, new_boyz_muted, 1)

# Non-layout wrap boxes. Bounding boxes are calculated from the already-rendered
# grid items, so no new grid row/column is introduced and existing spacing is not
# changed. The Unit wrap includes the open Unit row plus its visible detail,
# weapon header, every visible weapon, and every visible weapon-tag row. The
# selected-weapon wrap includes the selected weapon row and its tag row.
helper_marker = 'function ensurePersistentGridCells(){'
if view_np.count(helper_marker) != 1:
    raise SystemExit(f'wrap helper insertion marker: expected 1 match, found {view_np.count(helper_marker)}')

helpers = r'''function viewPresentationVisible(el){
  if(!el)return false;
  const style=getComputedStyle(el);
  return style.display!=='none'&&style.visibility!=='hidden'&&el.getClientRects().length>0;
}
function removeViewSelectionWraps(){
  grid.querySelectorAll('.view-open-unit-wrap,.view-selected-weapon-wrap').forEach(el=>el.remove());
}
function addViewSelectionWrap(className,anchor,nodes){
  if(!anchor||!viewPresentationVisible(anchor))return null;
  const gridRect=grid.getBoundingClientRect();
  const anchorRect=anchor.getBoundingClientRect();
  const rects=(Array.isArray(nodes)?nodes:[]).filter(viewPresentationVisible).map(el=>el.getBoundingClientRect());
  if(!rects.length)rects.push(anchorRect);
  const top=Math.min(anchorRect.top,...rects.map(rect=>rect.top));
  const bottom=Math.max(anchorRect.bottom,...rects.map(rect=>rect.bottom));
  const box=document.createElement('div');
  box.className=className;
  box.setAttribute('aria-hidden','true');
  box.style.left=String(Math.max(0,anchorRect.left-gridRect.left))+'px';
  box.style.top=String(Math.max(0,top-gridRect.top))+'px';
  box.style.width=String(anchorRect.width)+'px';
  box.style.height=String(Math.max(1,bottom-top))+'px';
  grid.appendChild(box);
  return box;
}
function selectedViewWeaponParts(){
  const row=grid.querySelector('.weapon-row.weapon-active,.boyz-subunit-weapon.weapon-active');
  if(!row||!viewPresentationVisible(row))return null;
  let tags=null;
  const weaponId=String(row.dataset.weaponId||'');
  if(weaponId){
    tags=[...grid.querySelectorAll('.boyz-subunit-tags')].find(el=>String(el.dataset.weaponId||'')===weaponId)||null;
  }
  if(!tags){
    const match=String(row.className||'').match(/(?:^|\s)weapon-row-(\d+)(?:\s|$)/);
    if(match)tags=grid.querySelector('.weapon-tags-'+match[1]);
  }
  return {row,tags:viewPresentationVisible(tags)?tags:null};
}
function syncViewSelectionPresentation(){
  if(typeof newViewHeaderLocked!=='undefined'&&newViewHeaderLocked)return;
  removeViewSelectionWraps();
  if(activePageMode!=='view'||activeUnitIndex===null)return;
  const activeRow=unitRow(activeUnitIndex);
  if(!activeRow||!viewPresentationVisible(activeRow))return;
  const unitParts=[activeRow];
  const detail=grid.querySelector('.detail-box-row');
  const header=grid.querySelector('.weapon-header:not(.boyz-subunit-node)');
  if(viewPresentationVisible(detail))unitParts.push(detail);
  if(viewPresentationVisible(header))unitParts.push(header);
  grid.querySelectorAll('.weapon-row,.weapon-tags,.boyz-subunit-node').forEach(el=>{
    if(viewPresentationVisible(el)&&!unitParts.includes(el))unitParts.push(el);
  });
  addViewSelectionWrap('view-open-unit-wrap',activeRow,unitParts);
  const selected=selectedViewWeaponParts();
  if(selected){
    const selectedParts=[selected.row];
    if(selected.tags)selectedParts.push(selected.tags);
    addViewSelectionWrap('view-selected-weapon-wrap',selected.row,selectedParts);
  }
}
const syncWeaponLayoutV31119=syncWeaponLayout;
syncWeaponLayout=function(){
  const result=syncWeaponLayoutV31119.apply(this,arguments);
  syncViewSelectionPresentation();
  return result;
};
const refreshBoyzNewViewSelectionV31119=refreshBoyzNewViewSelection;
refreshBoyzNewViewSelection=function(){
  const result=refreshBoyzNewViewSelectionV31119.apply(this,arguments);
  syncViewSelectionPresentation();
  return result;
};
window.addEventListener('resize',()=>{if(activePageMode==='view'&&!newViewHeaderLocked)syncViewSelectionPresentation()});
'''
view_np = view_np.replace(helper_marker, helpers + '\n' + helper_marker, 1)

text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.120
    Scope: Change unified New View selection presentation only. Unit/profile rows now start in the existing 50% muted treatment until opened; the open Unit keeps the established active styling and displays its name in CAPS. Visible normal and Boyz weapon rows/tags now start muted and only the selected weapon uses the existing active/unmuted treatment. Add a non-layout border around the currently open Unit from its name row through all visible detail/weapon/tag rows, plus a second border around the selected weapon and its associated tags. Both borders reuse the existing button/grid border color and do not add grid rows, padding, spacing, fonts, colors, or controls.
    Risk areas: Unified New View visual selection state and overlay borders only. Roster/weapon data, Unit/weapon click behavior, Boyz sub-unit logic, filters, lock/frozen state generation, scrolling, unified Edit, FIX reports, Version controls, Cards, persistence, CSV data, Waha routing, and Probable remain unchanged.
  -->

'''
marker = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.119\n'
if text.count(marker) != 1:
    raise SystemExit('V31.119 change-note insertion marker missing')
text = text.replace(marker, note + marker, 1)

# Keep only the five newest detailed V31 change notes.
notes = list(re.finditer(r'\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n', text, re.S))
for match in reversed(notes[5:]):
    text = text[:match.start()] + text[match.end():]

# Acceptance checks.
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing after writeback')
final_view = html.unescape(vm.group(2))
for expected in [
    '.view-unit-row:not(.unit-active) .view-unit-name,.view-unit-row:not(.unit-active) .view-unit-stat{opacity:.5}',
    '.view-unit-row.unit-active .view-unit-name{text-transform:uppercase}',
    '.draft-grid{position:relative}',
    '.view-open-unit-wrap,.view-selected-weapon-wrap{position:absolute;',
    'const muted=!active;',
    'function syncViewSelectionPresentation()',
    "addViewSelectionWrap('view-open-unit-wrap',activeRow,unitParts);",
    "addViewSelectionWrap('view-selected-weapon-wrap',selected.row,selectedParts);",
    'const syncWeaponLayoutV31119=syncWeaponLayout;',
    'const refreshBoyzNewViewSelectionV31119=refreshBoyzNewViewSelection;',
]:
    if expected not in final_view:
        raise SystemExit('V31.120 View acceptance failed: ' + expected)
if final_view.count('const muted=!active;') < 2:
    raise SystemExit('V31.120 default-muted acceptance failed for normal and Boyz weapons')
for forbidden in [
    'const muted=hasSelection&&!active;',
    'const muted=Boolean(selected)&&!active;',
]:
    if forbidden in final_view:
        raise SystemExit('V31.120 retained old selection-muted rule: ' + forbidden)

for expected in [
    '<title>WH40k 11th V31.120</title>',
    'The current baseline is WH40k_11th_V31.120;',
    'const APP_VERSION = "31.120";',
    "version: 'V31.120',",
    'CHANGE NOTE - WH40k_11th_V31.120',
]:
    if expected not in text:
        raise SystemExit('V31.120 release acceptance failed: ' + expected)

path.write_text(text, encoding='utf-8')
print('Built V31.120: default-muted View plus open-Unit and selected-weapon wrap boxes')
