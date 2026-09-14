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
replace_once("<title>WH40k 11th V31.145</title>", "<title>WH40k 11th V31.146</title>", "title")
replace_once(
    "The current baseline is WH40k_11th_V31.145;",
    "The current baseline is WH40k_11th_V31.146;",
    "baseline",
)
replace_once('const APP_VERSION = "31.145";', 'const APP_VERSION = "31.146";', "APP_VERSION")
replace_once("version: 'V31.145',", "version: 'V31.146',", "quality version")

# Phase 1: New View owns a lightweight, entry-scoped Ability activation gate.
# This does not alter Old View Tag state, CSV Default_Active, or any calculator yet.
parent_marker = "    window.toggleAlternateViewAbilityTag = function(payload = {}) {"
if text.count(parent_marker) != 1:
    raise SystemExit("V31.146 parent bridge insertion marker missing")
parent_bridge = r'''    // V31.146 New View-only Ability master gate. This transient state is keyed
    // by roster entry so duplicate Units remain independent. It is deliberately
    // separate from Old View abilityTagStates and CSV Default_Active.
    const newViewActiveAbilityKeysByEntry = new Map();

    window.setAlternateViewActiveAbilities = function(entryId, abilityKeys = []) {
      const cleanEntryId = String(entryId || "").trim();
      if (!cleanEntryId) return false;
      const cleanKeys = Array.isArray(abilityKeys)
        ? abilityKeys.map(key => String(key || "").trim()).filter(Boolean)
        : [];
      newViewActiveAbilityKeysByEntry.set(cleanEntryId, new Set(cleanKeys));
      return true;
    };

    window.getAlternateViewActiveAbilities = function(entryId) {
      const cleanEntryId = String(entryId || "").trim();
      if (!cleanEntryId) return [];
      const active = newViewActiveAbilityKeysByEntry.get(cleanEntryId);
      return active ? Array.from(active) : [];
    };

    window.isAlternateViewAbilityMechanicallyEligible = function(entryId, itemKey) {
      const cleanEntryId = String(entryId || "").trim();
      const cleanItemKey = String(itemKey || "").trim();
      if (!cleanEntryId || !cleanItemKey) return false;
      const active = newViewActiveAbilityKeysByEntry.get(cleanEntryId);
      return Boolean(active && active.has(cleanItemKey));
    };

'''
text = text.replace(parent_marker, parent_bridge + parent_marker, 1)

view_pat = re.compile(
    r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)',
    re.S,
)
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing")
view_np = html.unescape(vm.group(2))

for required in [
    "function newViewAbilityIsActive(key){",
    "function toggleNewViewAbilityActive(key){",
    "const activeAbilityKeys=new Set();",
    "function newViewProcessingLocked(){return Boolean(newViewHeaderLocked&&activePageMode==='view')}",
    "function renderNewViewAbilitiesAndReflow(){",
    "function toggleNewViewAbilityTag(key,tag){",
    "function toggleNewViewWeaponTag(weaponIndex,tagIndex){",
]:
    if required not in view_np:
        raise SystemExit("V31.146 baseline contract missing: " + required)

# Add a New View-only eligibility projection. Ability Active is now the sole
# master switch exposed for future Unit/Weapon/Probable mechanical consumers.
# Tags themselves are not changed in this phase.
old_active_helpers = '''function newViewAbilityIsActive(key){
  return activeAbilityKeys.has(newViewAbilityStateToken(key));
}
function newViewAbilityUsesLongDescription(key){
'''
new_active_helpers = '''function newViewAbilityIsActive(key){
  return activeAbilityKeys.has(newViewAbilityStateToken(key));
}
function newViewAbilityMechanicallyEligible(key){
  return Boolean(String(key||'')&&newViewAbilityIsActive(key));
}
function newViewActiveAbilityKeysForUnit(data){
  const abilities=Array.isArray(data&&data.abilities)?data.abilities:[];
  return abilities.map(ability=>String(ability&&ability.key||ability&&ability.abilityId||'')).filter(key=>key&&newViewAbilityMechanicallyEligible(key));
}
function syncNewViewAbilityMechanicalGate(data){
  if(activeUnitIndex===null)return false;
  const unitData=data||unitDataByIndex[activeUnitIndex];
  const entryId=String(unitData&&unitData.entryId||'').trim();
  if(!entryId)return false;
  const activeKeys=newViewActiveAbilityKeysForUnit(unitData);
  try{
    if(parent&&typeof parent.setAlternateViewActiveAbilities==='function'){
      return Boolean(parent.setAlternateViewActiveAbilities(entryId,activeKeys));
    }
  }catch(_){}
  return false;
}
function newViewAbilityUsesLongDescription(key){
'''
if view_np.count(old_active_helpers) != 1:
    raise SystemExit(f"V31.146 active helper insertion: expected 1 match, found {view_np.count(old_active_helpers)}")
view_np = view_np.replace(old_active_helpers, new_active_helpers, 1)

# Ability title activation is now the New View master mechanical switch. Lock
# blocks the state transition before either local state or the parent gate changes.
old_toggle = '''function toggleNewViewAbilityActive(key){
  const clean=String(key||'');
  const token=newViewAbilityStateToken(clean);
  if(activeAbilityKeys.has(token)){
    activeAbilityKeys.delete(token);
    if(String(selectedAbilityKey)===clean)selectedAbilityKey=null;
  }else{
    activeAbilityKeys.add(token);
    selectedAbilityKey=clean;
  }
  syncWeaponLayout();
}
'''
new_toggle = '''function toggleNewViewAbilityActive(key){
  if(newViewProcessingLocked())return false;
  const clean=String(key||'');
  const token=newViewAbilityStateToken(clean);
  if(activeAbilityKeys.has(token)){
    activeAbilityKeys.delete(token);
    if(String(selectedAbilityKey)===clean)selectedAbilityKey=null;
  }else{
    activeAbilityKeys.add(token);
    selectedAbilityKey=clean;
  }
  syncNewViewAbilityMechanicalGate();
  syncWeaponLayout();
  return true;
}
'''
if view_np.count(old_toggle) != 1:
    raise SystemExit(f"V31.146 Ability toggle: expected 1 match, found {view_np.count(old_toggle)}")
view_np = view_np.replace(old_toggle, new_toggle, 1)

# Keep the parent gate synchronized whenever New View renders the active Unit.
# This initializes an opened Unit to zero mechanically-active Abilities until the
# user explicitly activates one, without touching Tag state or CSV defaults.
old_render_start = '''  const data=unitDataByIndex[activeUnitIndex];
  if(!data)return 0;
  const activeRow=unitRow(activeUnitIndex);
'''
new_render_start = '''  const data=unitDataByIndex[activeUnitIndex];
  if(!data)return 0;
  syncNewViewAbilityMechanicalGate(data);
  const activeRow=unitRow(activeUnitIndex);
'''
if view_np.count(old_render_start) != 1:
    raise SystemExit(f"V31.146 Ability render gate sync: expected 1 match, found {view_np.count(old_render_start)}")
view_np = view_np.replace(old_render_start, new_render_start, 1)

text = text[: vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2) :]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.146
    Scope: Phase 1 of New View Ability-driven mechanics. New View now maintains a transient, roster-entry-scoped Ability master gate keyed by entryId + Ability key. Tapping an Ability title updates this gate: Active means that Ability is mechanically eligible for later Unit/Weapon/Probable consumers; Inactive means it is not eligible. An opened Unit initializes with no mechanically-active Abilities until explicitly activated. Duplicate roster Units remain independent. New View Lock blocks Ability activation/deactivation before the gate changes. This phase deliberately does not apply Unit-stat or Weapon-stat modifiers yet and does not change Tag clicking, Tag colors, Tag layout, Tag saved state, CSV Default_Active, Old View behavior, or any calculator.
    Risk areas: New View transient Ability activation/eligibility plumbing only. No Unit/Weapon mechanical application, Probable execution, Tag mutation/persistence, CSV data, Old View, grid/layout, typography, colors, Cards, Waha, FIX mode, or Version-control behavior changed.
  -->

'''
marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.145\n"
if text.count(marker) != 1:
    raise SystemExit("V31.145 change-note insertion marker missing")
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

# Focused Phase 1 acceptance checks.
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing after writeback")
final_view = html.unescape(vm.group(2))
for expected in [
    "function newViewAbilityMechanicallyEligible(key){",
    "function newViewActiveAbilityKeysForUnit(data){",
    "function syncNewViewAbilityMechanicalGate(data){",
    "if(newViewProcessingLocked())return false;",
    "syncNewViewAbilityMechanicalGate();",
    "syncNewViewAbilityMechanicalGate(data);",
    "function toggleNewViewAbilityTag(key,tag){",
    "function toggleNewViewWeaponTag(weaponIndex,tagIndex){",
]:
    if expected not in final_view:
        raise SystemExit("V31.146 New View acceptance failed: " + expected)

for expected in [
    "const newViewActiveAbilityKeysByEntry = new Map();",
    "window.setAlternateViewActiveAbilities = function(entryId, abilityKeys = []) {",
    "window.isAlternateViewAbilityMechanicallyEligible = function(entryId, itemKey) {",
    "<title>WH40k 11th V31.146</title>",
    "The current baseline is WH40k_11th_V31.146;",
    'const APP_VERSION = "31.146";',
    "version: 'V31.146',",
    "CHANGE NOTE - WH40k_11th_V31.146",
]:
    if expected not in text:
        raise SystemExit("V31.146 release acceptance failed: " + expected)

# Phase 1 must not consume the gate in the shared calculators or mutate Tag rules.
for forbidden in [
    "getRosterEntryAbilityTagState = function",
    "setRosterEntryAbilityTagState = function",
    "getRosterEntryEffectiveWeaponProfile = function",
]:
    if forbidden in parent_bridge:
        raise SystemExit("V31.146 Phase 1 scope violation: " + forbidden)

path.write_text(text, encoding="utf-8")
print("Built V31.146: New View Ability Active now owns an entry-scoped mechanical eligibility gate; no effects applied yet")
