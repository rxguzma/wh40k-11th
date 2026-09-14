from pathlib import Path
import html
import re

path = Path("WH40k_11th.html")
text = path.read_text(encoding="utf-8")


def replace_once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    text = text.replace(old, new, 1)


# Sequential release metadata.
replace_once("<title>WH40k 11th V31.130</title>", "<title>WH40k 11th V31.131</title>", "title")
replace_once(
    "The current baseline is WH40k_11th_V31.130;",
    "The current baseline is WH40k_11th_V31.131;",
    "baseline",
)
replace_once('const APP_VERSION = "31.130";', 'const APP_VERSION = "31.131";', "APP_VERSION")
replace_once("version: 'V31.130',", "version: 'V31.131',", "quality version")

view_pat = re.compile(
    r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)',
    re.S,
)
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing")
view_np = html.unescape(vm.group(2))

for required in [
    "function selectedViewWeaponParts(){",
    "function viewGridRowNumber(el){",
    "function syncViewSelectionPresentation(){",
    "function renderNewViewAbilitiesAndReflow(){",
    "function applyViewFocusSpacing(){",
    "const syncWeaponLayoutV31119=syncWeaponLayout;",
    "const refreshBoyzNewViewSelectionV31119=refreshBoyzNewViewSelection;",
    ".view-focus-separator{grid-column:1/span 16;",
]:
    if required not in view_np:
        raise SystemExit("V31.131 baseline contract missing: " + required)

# ---------------------------------------------------------------------------
# Weapon Tag focus layer.
# Keep every normally-visible Tag row until a Weapon is active. Once active,
# hide every other Weapon Tag row and compact only the Weapon stack. Ability
# layout is rendered afterward, so it naturally follows the compacted Weapon
# bottom. All state is presentation-only and reversible on the next interaction.
# ---------------------------------------------------------------------------
helper_anchor = "function syncViewSelectionPresentation(){"
if view_np.count(helper_anchor) != 1:
    raise SystemExit(f"weapon Tag helper anchor: expected 1 match, found {view_np.count(helper_anchor)}")
if "function applyViewWeaponTagFocus(){" in view_np:
    raise SystemExit("V31.131 weapon Tag focus helpers already present")

helpers = r'''let viewWeaponLayoutSyncDepth=0;
function restoreViewWeaponTagFocus(){
  grid.querySelectorAll('[data-view-tag-focus-display]').forEach(el=>{
    const original=el.dataset.viewTagFocusDisplay;
    if(original==='__EMPTY__')el.style.removeProperty('display');
    else el.style.display=original;
    delete el.dataset.viewTagFocusDisplay;
  });
  grid.querySelectorAll('[data-view-tag-focus-original-grid-row]').forEach(el=>{
    const original=el.dataset.viewTagFocusOriginalGridRow;
    if(original==='__EMPTY__')el.style.removeProperty('grid-row');
    else el.style.gridRow=original;
    delete el.dataset.viewTagFocusOriginalGridRow;
  });
}
function shiftViewWeaponTagFocusRow(el,delta){
  if(!el||!delta)return false;
  const row=viewGridRowNumber(el);
  if(!Number.isFinite(row))return false;
  if(!Object.prototype.hasOwnProperty.call(el.dataset,'viewTagFocusOriginalGridRow')){
    el.dataset.viewTagFocusOriginalGridRow=el.style.gridRow||'__EMPTY__';
  }
  const spanMatch=String(el.style.gridRow||'').match(/span\s+(\d+)/i);
  const span=spanMatch?Math.max(1,Number(spanMatch[1])||1):1;
  el.style.gridRow=String(row+delta)+(span>1?' / span '+String(span):'');
  return true;
}
function applyViewWeaponTagFocus(){
  if(activePageMode!=='view'||activeUnitIndex===null)return 0;
  const selected=selectedViewWeaponParts();
  if(!selected||!selected.row)return 0;
  const selectedTags=selected.tags||null;
  const hiddenRows=[];

  // Ability Tags are not Weapon Tags for this behavior and are deliberately
  // excluded. Existing filters/empty-tag visibility remain authoritative.
  grid.querySelectorAll('.weapon-tags:not(.unit-ability-tags)').forEach(tagRow=>{
    if(tagRow===selectedTags||!viewPresentationVisible(tagRow))return;
    const row=viewGridRowNumber(tagRow);
    if(Number.isFinite(row))hiddenRows.push(row);
    if(!Object.prototype.hasOwnProperty.call(tagRow.dataset,'viewTagFocusDisplay')){
      tagRow.dataset.viewTagFocusDisplay=tagRow.style.display||'__EMPTY__';
    }
    tagRow.style.display='none';
  });

  const rows=[...new Set(hiddenRows)].sort((a,b)=>a-b);
  if(!rows.length)return 0;
  const hiddenBefore=row=>rows.reduce((count,hiddenRow)=>count+(hiddenRow<row?1:0),0);
  const shifted=new Set();
  const compact=el=>{
    if(!el||shifted.has(el)||!viewPresentationVisible(el))return;
    shifted.add(el);
    const row=viewGridRowNumber(el);
    if(!Number.isFinite(row))return;
    const amount=hiddenBefore(row);
    if(amount)shiftViewWeaponTagFocusRow(el,-amount);
  };

  compact(grid.querySelector('.weapon-header:not(.boyz-subunit-node)'));
  grid.querySelectorAll('.weapon-row,.weapon-tags:not(.unit-ability-tags),.boyz-subunit-node').forEach(compact);
  return rows.length;
}
'''
view_np = view_np.replace(helper_anchor, helpers + "\n" + helper_anchor, 1)

# The current normal Weapon wrapper already rebuilds Abilities after the base
# Weapon layout. Insert Tag focus between those two stages, then let the existing
# Ability reflow and gray focus-zone spacing use the compacted Weapon stack.
old_sync_wrapper = r'''syncWeaponLayout=function(){
  const focusLocked=typeof newViewHeaderLocked!=='undefined'&&newViewHeaderLocked;
  if(!focusLocked)clearViewFocusSpacing();
  const result=syncWeaponLayoutV31119.apply(this,arguments);
  renderNewViewAbilitiesAndReflow();
  if(!focusLocked)applyViewFocusSpacing();
  syncViewSelectionPresentation();
  return result;
};'''
new_sync_wrapper = r'''syncWeaponLayout=function(){
  const focusLocked=typeof newViewHeaderLocked!=='undefined'&&newViewHeaderLocked;
  if(!focusLocked){
    clearViewFocusSpacing();
    restoreViewWeaponTagFocus();
  }
  let result;
  viewWeaponLayoutSyncDepth++;
  try{result=syncWeaponLayoutV31119.apply(this,arguments)}
  finally{viewWeaponLayoutSyncDepth=Math.max(0,viewWeaponLayoutSyncDepth-1)}
  if(!focusLocked)applyViewWeaponTagFocus();
  renderNewViewAbilitiesAndReflow();
  if(!focusLocked)applyViewFocusSpacing();
  syncViewSelectionPresentation();
  return result;
};'''
if view_np.count(old_sync_wrapper) != 1:
    raise SystemExit(f"normal Weapon wrapper: expected 1 match, found {view_np.count(old_sync_wrapper)}")
view_np = view_np.replace(old_sync_wrapper, new_sync_wrapper, 1)

# Boyz weapon clicks normally call refreshBoyzNewViewSelection directly instead
# of the full normal Weapon layout. Give direct Boyz clicks the same Tag-focus /
# Ability-reflow path. When that refresh is invoked from inside the full layout,
# the depth guard leaves all presentation work to the outer wrapper, preventing
# duplicate focus spacing.
old_boyz_wrapper = r'''refreshBoyzNewViewSelection=function(){
  const focusLocked=typeof newViewHeaderLocked!=='undefined'&&newViewHeaderLocked;
  if(!focusLocked)clearViewFocusSpacing();
  const result=refreshBoyzNewViewSelectionV31119.apply(this,arguments);
  if(!focusLocked)applyViewFocusSpacing();
  syncViewSelectionPresentation();
  return result;
};'''
new_boyz_wrapper = r'''refreshBoyzNewViewSelection=function(){
  const focusLocked=typeof newViewHeaderLocked!=='undefined'&&newViewHeaderLocked;
  const nested=viewWeaponLayoutSyncDepth>0;
  if(!focusLocked&&!nested){
    clearViewFocusSpacing();
    restoreViewWeaponTagFocus();
  }
  const result=refreshBoyzNewViewSelectionV31119.apply(this,arguments);
  if(!focusLocked&&!nested){
    applyViewWeaponTagFocus();
    renderNewViewAbilitiesAndReflow();
    applyViewFocusSpacing();
  }
  if(!nested)syncViewSelectionPresentation();
  return result;
};'''
if view_np.count(old_boyz_wrapper) != 1:
    raise SystemExit(f"Boyz Weapon wrapper: expected 1 match, found {view_np.count(old_boyz_wrapper)}")
view_np = view_np.replace(old_boyz_wrapper, new_boyz_wrapper, 1)

# Resize must restore Tag-focus row coordinates before focus spacing is rebuilt,
# then reapply Tag focus, Ability reflow, focus separators, and overlay boxes in
# the same order as an interaction.
old_resize = "window.addEventListener('resize',()=>{if(activePageMode==='view'&&!newViewHeaderLocked){clearViewFocusSpacing();applyViewFocusSpacing();syncViewSelectionPresentation()}});"
new_resize = "window.addEventListener('resize',()=>{if(activePageMode==='view'&&!newViewHeaderLocked){clearViewFocusSpacing();restoreViewWeaponTagFocus();applyViewWeaponTagFocus();renderNewViewAbilitiesAndReflow();applyViewFocusSpacing();syncViewSelectionPresentation()}});"
if view_np.count(old_resize) != 1:
    raise SystemExit(f"View resize handler: expected 1 match, found {view_np.count(old_resize)}")
view_np = view_np.replace(old_resize, new_resize, 1)

text = text[: vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2) :]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.131
    Scope: Add active-Weapon Tag focus in unified New View. With no Weapon selected, every Weapon Tag row that is normally visible remains visible in the existing muted treatment. When a Weapon becomes active, only that Weapon's separate Tag row remains visible; all other Weapon Tag rows disappear while every Weapon name/stat row remains visible. The Weapon stack compacts by exactly the removed Tag rows, existing Unit Abilities reflow immediately below the compacted Weapon area, the gray focus separators and open-Unit wrap continue to bound the visible Unit content, and the selected-Weapon wrap includes the active Tag row when present. Selecting a different Weapon switches the visible Tag row; deselecting restores all normally-visible muted Weapon Tag rows. Boyz sub-unit Weapons use the same behavior.
    Risk areas: Unified New View Weapon Tag-row visibility/compaction and Boyz direct-selection reflow only. Ability Tags are explicitly excluded. No Weapon/Ability data, filter semantics, Unit stats, Edit, CSV data, lock/frozen state, FIX reports, Cards, Waha, Probable, persistence, or Version-control behavior changes.
  -->

'''
marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.130\n"
if text.count(marker) != 1:
    raise SystemExit("V31.130 change-note insertion marker missing")
text = text.replace(marker, note + marker, 1)

# Keep only the five newest detailed V31 change notes.
notes = list(
    re.finditer(
        r"\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n",
        text,
        re.S,
    )
)
for match in reversed(notes[5:]):
    text = text[: match.start()] + text[match.end() :]

# Focused acceptance checks.
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing after writeback")
final_view = html.unescape(vm.group(2))
for expected in [
    "let viewWeaponLayoutSyncDepth=0;",
    "function restoreViewWeaponTagFocus(){",
    "function applyViewWeaponTagFocus(){",
    "grid.querySelectorAll('.weapon-tags:not(.unit-ability-tags)').forEach(tagRow=>{",
    "if(tagRow===selectedTags||!viewPresentationVisible(tagRow))return;",
    "tagRow.style.display='none';",
    "grid.querySelectorAll('.weapon-row,.weapon-tags:not(.unit-ability-tags),.boyz-subunit-node').forEach(compact);",
    "viewWeaponLayoutSyncDepth++;",
    "finally{viewWeaponLayoutSyncDepth=Math.max(0,viewWeaponLayoutSyncDepth-1)}",
    "if(!focusLocked)applyViewWeaponTagFocus();",
    "renderNewViewAbilitiesAndReflow();",
    "const nested=viewWeaponLayoutSyncDepth>0;",
    "if(!nested)syncViewSelectionPresentation();",
    "restoreViewWeaponTagFocus();applyViewWeaponTagFocus();renderNewViewAbilitiesAndReflow();applyViewFocusSpacing();",
    "addViewSelectionWrap('view-selected-weapon-wrap',selected.row,selectedParts);",
    ".view-focus-separator{grid-column:1/span 16;",
]:
    if expected not in final_view:
        raise SystemExit("V31.131 View acceptance failed: " + expected)

for expected in [
    "<title>WH40k 11th V31.131</title>",
    "The current baseline is WH40k_11th_V31.131;",
    'const APP_VERSION = "31.131";',
    "version: 'V31.131',",
    "CHANGE NOTE - WH40k_11th_V31.131",
]:
    if expected not in text:
        raise SystemExit("V31.131 release acceptance failed: " + expected)

path.write_text(text, encoding="utf-8")
print("Built V31.131: selected Weapon keeps only its own separate Tag row visible")
