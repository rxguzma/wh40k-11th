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
replace_once("<title>WH40k 11th V31.144</title>", "<title>WH40k 11th V31.145</title>", "title")
replace_once(
    "The current baseline is WH40k_11th_V31.144;",
    "The current baseline is WH40k_11th_V31.145;",
    "baseline",
)
replace_once('const APP_VERSION = "31.144";', 'const APP_VERSION = "31.145";', "APP_VERSION")
replace_once("version: 'V31.144',", "version: 'V31.145',", "quality version")

# Parent bridge: when New View asks for one clicked Unit after a Tag mutation,
# resolve and build only that roster entry. Do not build every roster model.
old_unit_data_head = '''    window.getAlternateViewUnitData = function(index) {
      const roster = appEditMode && viewEditRosterDraft ? getViewEditRoster() : getActiveRoster();
      const models = getRosterEntryModels(roster).filter(item => item && !item.isSpacer && !item.isNote && !item.isDeleted && !item.isMissingUnit);
      const model = models[Math.max(0, Number(index) || 0)] || null;
      if (!model) return null;
'''
new_unit_data_head = '''    window.getAlternateViewUnitData = function(index, entryId = "") {
      const roster = appEditMode && viewEditRosterDraft ? getViewEditRoster() : getActiveRoster();
      const requestedEntryId = String(entryId || "").trim();
      let model = null;
      if (requestedEntryId && roster && Array.isArray(roster.entries)) {
        const entryIndex = roster.entries.findIndex(item => item && String(item.entryId || "").trim() === requestedEntryId);
        const targetEntry = entryIndex >= 0 ? roster.entries[entryIndex] : null;
        if (targetEntry && !isSpacerEntry(targetEntry) && !isRosterNoteEntry(targetEntry) && !isRosterEntryPendingDeletion(targetEntry)) {
          model = getRosterEntryModel(targetEntry, entryIndex, roster, null);
          if (model && (model.isSpacer || model.isNote || model.isDeleted || model.isMissingUnit)) model = null;
        }
      } else {
        const models = getRosterEntryModels(roster).filter(item => item && !item.isSpacer && !item.isNote && !item.isDeleted && !item.isMissingUnit);
        model = models[Math.max(0, Number(index) || 0)] || null;
      }
      if (!model) return null;
'''
replace_once(old_unit_data_head, new_unit_data_head, "single-entry New View data bridge")

view_pat = re.compile(
    r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)',
    re.S,
)
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing")
view_np = html.unescape(vm.group(2))

old_refresh = '''function refreshNewViewAfterTagMutation(){
  if(newViewProcessingLocked())return false;
  const currentData=activeUnitIndex===null?null:unitDataByIndex[activeUnitIndex];
  const savedEntryId=String(currentData&&currentData.entryId||'');
  const savedWeapon=selectedWeaponIndex!==null&&currentData&&Array.isArray(currentData.weapons)?currentData.weapons[selectedWeaponIndex-1]:null;
  const savedWeaponId=String(savedWeapon&&savedWeapon.weaponId||'');
  const savedAbility=selectedAbilityKey;
  let rows=[];
  try{rows=parent&&typeof parent.getAlternateViewRosterRows==='function'?parent.getAlternateViewRosterRows():[]}catch(_){rows=[]}
  const ok=renderNewViewRosterRows(rows);
  if(savedEntryId){
    const restoredIndex=rows.findIndex(row=>row&&row.kind==='unit'&&String(row.entryId||'')===savedEntryId);
    if(restoredIndex>=0)activeUnitIndex=restoredIndex;
  }
  selectedWeaponIndex=null;
  const restoredData=activeUnitIndex===null?null:unitDataByIndex[activeUnitIndex];
  if(savedWeaponId&&restoredData&&Array.isArray(restoredData.weapons)){
    const restoredWeaponIndex=restoredData.weapons.findIndex(weapon=>String(weapon&&weapon.weaponId||'')===savedWeaponId);
    if(restoredWeaponIndex>=0)selectedWeaponIndex=restoredWeaponIndex+1;
  }
  selectedAbilityKey=savedAbility;
  applyActiveUnitDetails();
  syncUnitDetailVisibility();
  refreshNewViewTitleFromLegacy();
  cachedLiveViewHeader=captureNewViewHeaderSnapshot();
  hasLiveViewCache=true;
  return ok;
}
'''
new_refresh = '''function refreshNewViewAfterTagMutation(){
  if(newViewProcessingLocked()||activeUnitIndex===null)return false;
  const rowIndex=activeUnitIndex;
  const currentData=unitDataByIndex[rowIndex];
  const entryId=String(currentData&&currentData.entryId||'').trim();
  if(!currentData||!entryId)return false;
  const savedWeapon=selectedWeaponIndex!==null&&Array.isArray(currentData.weapons)?currentData.weapons[selectedWeaponIndex-1]:null;
  const savedWeaponId=String(savedWeapon&&savedWeapon.weaponId||'');
  const savedAbility=selectedAbilityKey;
  let fresh=null;
  try{
    if(parent&&typeof parent.getAlternateViewUnitData==='function')fresh=parent.getAlternateViewUnitData(0,entryId);
  }catch(_){fresh=null}
  if(!fresh)return false;
  const nextData=Object.assign({},currentData,fresh,{kind:'unit',entryId});
  unitDataByIndex[rowIndex]=nextData;
  if(Array.isArray(currentViewRosterRows)&&currentViewRosterRows[rowIndex]&&currentViewRosterRows[rowIndex].kind==='unit'){
    currentViewRosterRows[rowIndex]=Object.assign({},currentViewRosterRows[rowIndex],fresh,{kind:'unit',entryId});
  }
  selectedWeaponIndex=null;
  if(savedWeaponId&&Array.isArray(nextData.weapons)){
    const restoredWeaponIndex=nextData.weapons.findIndex(weapon=>String(weapon&&weapon.weaponId||'')===savedWeaponId);
    if(restoredWeaponIndex>=0)selectedWeaponIndex=restoredWeaponIndex+1;
  }
  selectedAbilityKey=savedAbility;
  applyActiveUnitDetails();
  syncUnitDetailVisibility();
  return true;
}
'''
if view_np.count(old_refresh) != 1:
    raise SystemExit(f"unit-scoped Tag refresh: expected 1 V31.143/V31.144 helper, found {view_np.count(old_refresh)}")
view_np = view_np.replace(old_refresh, new_refresh, 1)

# V31.145 must keep all existing V31.144 visual and interaction rules intact.
for required in [
    "const displayActive=weaponSelected;",
    "function toggleNewViewAbilityTag(key,tag){",
    "function toggleNewViewWeaponTag(weaponIndex,tagIndex){",
    "function toggleBoyzNewViewWeaponTag(weaponId,tagIndex){",
    "function newViewProcessingLocked(){return Boolean(newViewHeaderLocked&&activePageMode==='view')}",
]:
    if required not in view_np:
        raise SystemExit("V31.145 baseline contract missing: " + required)

text = text[: vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2) :]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.145
    Scope: New View Tag performance. A Tag mutation is now strictly Unit-scoped. The parent New View data bridge accepts the clicked roster entryId and builds only that single roster-entry model instead of calling getRosterEntryModels() across the full roster. After a successful Ability or Weapon Tag toggle, New View replaces only the active Unit's cached data and redraws only that Unit's open details. It no longer calls getAlternateViewRosterRows(), renderNewViewRosterRows(), title/header refresh, Version layout, or any other roster-wide New View refresh from a Tag tap. The selected Weapon and Ability presentation state are preserved. New View Lock remains a hard gate before any Tag write or refresh.
    Risk areas: Tag-tap refresh scope only. Existing V31.144 Tag colors/presentation, Tag persistence, per-unit state, locked/innate Tags, Unit/Weapon selection rules, grid/layout, Probable activation policy, FIX mode, Cards, Waha, Edit, and CSV data are unchanged.
  -->

'''
marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.144\n"
if text.count(marker) != 1:
    raise SystemExit("V31.144 change-note insertion marker missing")
text = text.replace(marker, note + marker, 1)

# Keep only the five newest detailed V31 change notes.
notes = list(re.finditer(r"\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n", text, re.S))
for match in reversed(notes[5:]):
    text = text[:match.start()] + text[match.end():]

# Focused acceptance checks.
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing after writeback")
final_view = html.unescape(vm.group(2))
for expected in [
    "fresh=parent.getAlternateViewUnitData(0,entryId);",
    "unitDataByIndex[rowIndex]=nextData;",
    "currentViewRosterRows[rowIndex]=Object.assign({},currentViewRosterRows[rowIndex],fresh,{kind:'unit',entryId});",
    "applyActiveUnitDetails();",
    "syncUnitDetailVisibility();",
    "const displayActive=weaponSelected;",
]:
    if expected not in final_view:
        raise SystemExit("V31.145 View acceptance failed: " + expected)

refresh_start = final_view.find("function refreshNewViewAfterTagMutation(){")
refresh_end = final_view.find("\nfunction toggleNewViewAbilityTag", refresh_start)
if refresh_start < 0 or refresh_end < 0:
    raise SystemExit("V31.145 refresh helper bounds missing")
refresh_body = final_view[refresh_start:refresh_end]
for forbidden in [
    "getAlternateViewRosterRows",
    "renderNewViewRosterRows",
    "refreshNewViewTitleFromLegacy",
    "captureNewViewHeaderSnapshot",
]:
    if forbidden in refresh_body:
        raise SystemExit("V31.145 acceptance failed: roster-wide work remains in Tag refresh: " + forbidden)

for expected in [
    'window.getAlternateViewUnitData = function(index, entryId = "")',
    "model = getRosterEntryModel(targetEntry, entryIndex, roster, null);",
    "<title>WH40k 11th V31.145</title>",
    "The current baseline is WH40k_11th_V31.145;",
    'const APP_VERSION = "31.145";',
    "version: 'V31.145',",
    "CHANGE NOTE - WH40k_11th_V31.145",
]:
    if expected not in text:
        raise SystemExit("V31.145 release acceptance failed: " + expected)

path.write_text(text, encoding="utf-8")
print("Built V31.145: Tag taps rebuild and redraw only their attached Unit")
