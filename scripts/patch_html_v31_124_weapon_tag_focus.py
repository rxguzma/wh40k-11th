from pathlib import Path
import html
import re

path = Path("WH40k_11th.html")
text = path.read_text(encoding="utf-8")


def once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    text = text.replace(old, new, 1)


# Sequential release metadata.
once("<title>WH40k 11th V31.123</title>", "<title>WH40k 11th V31.124</title>", "title")
once(
    "The current baseline is WH40k_11th_V31.123;",
    "The current baseline is WH40k_11th_V31.124;",
    "baseline",
)
once('const APP_VERSION = "31.123";', 'const APP_VERSION = "31.124";', "APP_VERSION")
once("version: 'V31.123',", "version: 'V31.124',", "quality version")

view_pat = re.compile(
    r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)',
    re.S,
)
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing")
view_np = html.unescape(vm.group(2))

# V31.124: when a weapon is selected, keep only that weapon's separate Tag row
# visible. Weapon rows stay visible. With no selected weapon, the existing base
# renderer remains authoritative and all normally-visible Tag rows return.
helper_anchor = "function syncViewSelectionPresentation(){"
if view_np.count(helper_anchor) != 1:
    raise SystemExit(f"tag-focus helper anchor: expected 1 match, found {view_np.count(helper_anchor)}")
if "function applyViewWeaponTagFocus(){" in view_np:
    raise SystemExit("V31.124 weapon Tag focus helpers already present")

helpers = r'''function restoreViewWeaponTagFocus(){
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
  if(typeof positionNewViewVersionControls==='function')positionNewViewVersionControls();
}
function shiftViewTagFocusGridRow(el,delta){
  if(!el||!delta)return false;
  const row=viewGridRowNumber(el);
  if(!Number.isFinite(row))return false;
  if(!Object.prototype.hasOwnProperty.call(el.dataset,'viewTagFocusOriginalGridRow')){
    el.dataset.viewTagFocusOriginalGridRow=el.style.gridRow||'__EMPTY__';
  }
  el.style.gridRow=String(row+delta);
  return true;
}
function applyViewWeaponTagFocus(){
  if(activePageMode!=='view'||activeUnitIndex===null)return;
  const selected=selectedViewWeaponParts();
  if(!selected||!selected.row)return;
  const selectedTags=selected.tags||null;
  const hiddenRows=[];

  // Hide only Tag rows that the existing renderer currently considers visible.
  // This preserves Range/Melee/Other filter visibility and empty-tag behavior.
  grid.querySelectorAll('.weapon-tags,.boyz-subunit-tags').forEach(tagRow=>{
    if(tagRow===selectedTags||!viewPresentationVisible(tagRow))return;
    const row=viewGridRowNumber(tagRow);
    if(Number.isFinite(row))hiddenRows.push(row);
    if(!Object.prototype.hasOwnProperty.call(tagRow.dataset,'viewTagFocusDisplay')){
      tagRow.dataset.viewTagFocusDisplay=tagRow.style.display||'__EMPTY__';
    }
    tagRow.style.display='none';
  });

  const rows=[...new Set(hiddenRows)].sort((a,b)=>a-b);
  if(!rows.length){
    if(typeof syncNewViewFrameHeight==='function')syncNewViewFrameHeight();
    return;
  }

  const activeRow=unitRow(activeUnitIndex);
  const activeBaseRow=viewGridRowNumber(activeRow);
  if(!Number.isFinite(activeBaseRow))return;
  const hiddenBefore=row=>rows.reduce((count,hiddenRow)=>count+(hiddenRow<row?1:0),0);

  // Compact the expanded content while preserving the original row order. Only
  // rows made invisible by weapon Tag focus are removed from the vertical stack.
  const shifted=new Set();
  const compactElement=el=>{
    if(!el||shifted.has(el)||!viewPresentationVisible(el))return;
    shifted.add(el);
    const row=viewGridRowNumber(el);
    if(!Number.isFinite(row))return;
    const amount=hiddenBefore(row);
    if(amount)shiftViewTagFocusGridRow(el,-amount);
  };
  compactElement(grid.querySelector('.detail-box-row'));
  compactElement(grid.querySelector('.weapon-header:not(.boyz-subunit-node)'));
  grid.querySelectorAll('.weapon-row,.weapon-tags,.boyz-subunit-node').forEach(compactElement);

  // The base layout allocated one roster row for each Tag row we just hid, so
  // move every later roster row upward by the exact number removed.
  grid.querySelectorAll('.dynamic-roster-row').forEach(el=>{
    if(el===activeRow)return;
    const row=viewGridRowNumber(el);
    if(Number.isFinite(row)&&row>activeBaseRow)shiftViewTagFocusGridRow(el,-rows.length);
  });
  const mainButton=grid.querySelector('.top-main-button');
  if(mainButton&&viewGridRowNumber(mainButton)>activeBaseRow){
    shiftViewTagFocusGridRow(mainButton,-rows.length);
  }
  if(typeof positionNewViewVersionControls==='function')positionNewViewVersionControls();
  if(typeof syncNewViewFrameHeight==='function')syncNewViewFrameHeight();
}
'''
view_np = view_np.replace(helper_anchor, helpers + "\n" + helper_anchor, 1)

# Run Tag focus between the authoritative base weapon layout and V31.123's gray
# separator spacing. Restore it first on every interaction so filters and weapon
# selection always start from the renderer's normal full Tag-row layout.
old_sync_wrapper = r'''syncWeaponLayout=function(){
  const focusLocked=typeof newViewHeaderLocked!=='undefined'&&newViewHeaderLocked;
  if(!focusLocked)clearViewFocusSpacing();
  const result=syncWeaponLayoutV31119.apply(this,arguments);
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
  const result=syncWeaponLayoutV31119.apply(this,arguments);
  if(!focusLocked){
    applyViewWeaponTagFocus();
    applyViewFocusSpacing();
  }
  syncViewSelectionPresentation();
  return result;
};'''
if view_np.count(old_sync_wrapper) != 1:
    raise SystemExit(f"normal weapon Tag-focus wrapper: expected 1 match, found {view_np.count(old_sync_wrapper)}")
view_np = view_np.replace(old_sync_wrapper, new_sync_wrapper, 1)

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
  if(!focusLocked){
    clearViewFocusSpacing();
    restoreViewWeaponTagFocus();
  }
  const result=refreshBoyzNewViewSelectionV31119.apply(this,arguments);
  if(!focusLocked){
    applyViewWeaponTagFocus();
    applyViewFocusSpacing();
  }
  syncViewSelectionPresentation();
  return result;
};'''
if view_np.count(old_boyz_wrapper) != 1:
    raise SystemExit(f"Boyz weapon Tag-focus wrapper: expected 1 match, found {view_np.count(old_boyz_wrapper)}")
view_np = view_np.replace(old_boyz_wrapper, new_boyz_wrapper, 1)

text = text[: vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2) :]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.124
    Scope: Focus weapon Tag rows in unified View. Before a weapon is selected, all Tag rows that are normally visible remain visible in the existing muted treatment. Once a weapon is active, only that weapon's separate Tag row remains visible; Tag rows belonging to every other visible weapon are removed from the expanded vertical stack while all weapon name/stat rows remain visible. Selecting another weapon moves Tag focus to that weapon. Deselecting the active weapon restores the normal visible muted Tag rows. Existing Range/Melee/Other filtering, Unit and selected-Weapon wrap boxes, and gray focus separator rows are preserved.
    Risk areas: Unified View weapon Tag-row visibility and expanded-row compaction only. Weapon data/content, active selection semantics, Unit focus, Boyz selection, filters, lock/frozen behavior, scrolling/frame sizing, Edit, FIX, Cards, persistence, CSV data, Waha routing, Probable, and Version controls remain unchanged.
  -->

'''
marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.123\n"
if text.count(marker) != 1:
    raise SystemExit("V31.123 change-note insertion marker missing")
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

# Acceptance checks.
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing after writeback")
final_view = html.unescape(vm.group(2))
for expected in [
    "function restoreViewWeaponTagFocus(){",
    "function applyViewWeaponTagFocus(){",
    "grid.querySelectorAll('.weapon-tags,.boyz-subunit-tags').forEach(tagRow=>{",
    "if(tagRow===selectedTags||!viewPresentationVisible(tagRow))return;",
    "tagRow.style.display='none';",
    "grid.querySelectorAll('.dynamic-roster-row').forEach(el=>{",
    "shiftViewTagFocusGridRow(el,-rows.length);",
    "restoreViewWeaponTagFocus();",
    "applyViewWeaponTagFocus();",
    "applyViewFocusSpacing();",
    "function syncViewSelectionPresentation(){",
    "addViewSelectionWrap('view-selected-weapon-wrap',selected.row,selectedParts);",
    ".view-focus-separator{grid-column:1/span 16;height:var(--cell);",
]:
    if expected not in final_view:
        raise SystemExit("V31.124 View acceptance failed: " + expected)

for expected in [
    "<title>WH40k 11th V31.124</title>",
    "The current baseline is WH40k_11th_V31.124;",
    'const APP_VERSION = "31.124";',
    "version: 'V31.124',",
    "CHANGE NOTE - WH40k_11th_V31.124",
]:
    if expected not in text:
        raise SystemExit("V31.124 release acceptance failed: " + expected)

path.write_text(text, encoding="utf-8")
print("Built V31.124: active weapon keeps only its own Tag row visible")
