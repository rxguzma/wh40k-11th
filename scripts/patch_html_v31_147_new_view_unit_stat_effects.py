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
replace_once("<title>WH40k 11th V31.146</title>", "<title>WH40k 11th V31.147</title>", "title")
replace_once(
    "The current baseline is WH40k_11th_V31.146;",
    "The current baseline is WH40k_11th_V31.147;",
    "baseline",
)
replace_once('const APP_VERSION = "31.146";', 'const APP_VERSION = "31.147";', "APP_VERSION")
replace_once("version: 'V31.146',", "version: 'V31.147',", "quality version")

# ---------------------------------------------------------------------------
# Phase 2: project New View Unit stats through the existing structured Unit
# profile engine, but suppress Unit-stat Tags belonging to inactive New View
# Abilities. Persistent roster Tag state itself is never changed.
# ---------------------------------------------------------------------------
parent_marker = '    window.toggleAlternateViewAbilityTag = function(payload = {}) {'
if text.count(parent_marker) != 1:
    raise SystemExit("V31.147 parent helper insertion marker missing")

parent_helper = r'''    function getAlternateViewEffectiveUnitStats(entry, unit, roster, fallbackStats = {}) {
      if (!entry || !unit) return fallbackStats || {};

      // Work on a detached Tag-state projection so inactive New View Abilities
      // can contribute zero Unit-stat effects without mutating saved roster state.
      const projectedEntry = {
        ...entry,
        abilityTagStates: JSON.parse(JSON.stringify(entry.abilityTagStates || {}))
      };

      getAbilitiesForRosterEntry(entry, unit)
        .filter(ability => ability && !ability.isMissingLink)
        .forEach((ability, sequence) => {
          const sourceItem = getAbilitySourceItem(ability) || ability;
          const effectiveItem = getRosterEntryEffectiveAbility(entry, sourceItem) || sourceItem;
          const rawItemKey = getAbilityItemEditKey(sourceItem) || sourceItem.abilityId || sourceItem.name || sequence;
          const itemKey = String(rawItemKey ?? "").trim();

          // Active Ability title = mechanically eligible. Its individual saved
          // Tag On/Off states flow through unchanged into getEffectiveUnitProfile.
          if (itemKey && window.isAlternateViewAbilityMechanicallyEligible(entry.entryId, itemKey)) return;

          const defaultOn = getRosterTaggedSourceDefaultActive("ability", sourceItem);
          getAbilityProtectedModifierTagAssignments(effectiveItem).forEach(assignment => {
            const effect = getStructuredTagDefinitionEffect(assignment.tag, assignment.category);
            const effectType = String(effect && (effect.effectType || effect.type) || "").trim().toUpperCase();
            const target = String(effect && effect.target || "").trim().toUpperCase();

            // Phase 2 is Unit stats only. Weapon effects, rules, rerolls, points,
            // descriptions, and all other effect types are intentionally untouched.
            if (!["STAT", "UNIT_STAT"].includes(effectType) || target !== "UNIT") return;

            setRosterEntryAbilityTagState(
              projectedEntry,
              sourceItem,
              assignment.tag,
              false,
              defaultOn,
              assignment.category
            );
          });
        });

      const profile = getEffectiveUnitProfile(projectedEntry, unit, roster);
      return profile && profile.stats ? profile.stats : (fallbackStats || {});
    };

'''
text = text.replace(parent_marker, parent_helper + parent_marker, 1)

# Use the New View-only projected stats instead of the already-built roster model
# stats. Existing getEffectiveUnitProfile remains the single stat-effects engine.
old_stats_block = '''      const stats = model.stats || {};
      const entry = model.entry || (roster && Array.isArray(roster.entries) ? roster.entries.find(item => item && item.entryId === model.entryId) : null);
      const unit = model.unit || (entry ? getUnitById(entry.unitId) : null);
'''
new_stats_block = '''      const baseStats = model.stats || {};
      const entry = model.entry || (roster && Array.isArray(roster.entries) ? roster.entries.find(item => item && item.entryId === model.entryId) : null);
      const unit = model.unit || (entry ? getUnitById(entry.unitId) : null);
      const stats = entry && unit
        ? getAlternateViewEffectiveUnitStats(entry, unit, roster, baseStats)
        : baseStats;
'''
replace_once(old_stats_block, new_stats_block, "New View Unit-stat projection")

# New View Ability-title changes now re-fetch only the active Unit after the
# master gate changes, so M/T/SV/W/LD/OC immediately reflect active Ability Tags.
# This uses the V31.145 Unit-scoped refresh and does not initialize Probable.
view_pat = re.compile(
    r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)',
    re.S,
)
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing")
view_np = html.unescape(vm.group(2))

old_toggle_tail = '''  syncNewViewAbilityMechanicalGate();
  syncWeaponLayout();
  return true;
}
'''
new_toggle_tail = '''  syncNewViewAbilityMechanicalGate();
  if(!refreshNewViewAfterTagMutation())syncWeaponLayout();
  return true;
}
'''
if view_np.count(old_toggle_tail) != 1:
    raise SystemExit(f"V31.147 Ability-title refresh: expected 1 match, found {view_np.count(old_toggle_tail)}")
view_np = view_np.replace(old_toggle_tail, new_toggle_tail, 1)

for required in [
    "function refreshNewViewAfterTagMutation(){",
    "function toggleNewViewAbilityTag(key,tag){",
    "function toggleNewViewWeaponTag(weaponIndex,tagIndex){",
    "function toggleBoyzNewViewWeaponTag(weaponId,tagIndex){",
    "function newViewProcessingLocked(){return Boolean(newViewHeaderLocked&&activePageMode==='view')}",
]:
    if required not in view_np:
        raise SystemExit("V31.147 baseline New View contract missing: " + required)

text = text[: vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2) :]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.147
    Scope: Phase 2 of New View Ability-driven mechanics. Active Ability titles now gate structured Unit-stat effects in New View. For an active Ability, its existing per-roster Tag On/Off state is respected by the existing effective Unit-profile engine. For an inactive Ability, only structured STAT/UNIT_STAT effects targeting UNIT are suppressed in a detached projection, so the saved Tag state is not changed. M, T, SV/Invul, W, LD, and OC update immediately through the existing Unit-scoped New View refresh. No Short/Long Description text is parsed. Weapon effects are not added in this phase, and Probable remains lazy and is not initialized by Ability or Tag changes. Lock remains a hard gate before Ability or Tag mutation.
    Risk areas: New View Unit-stat projection and Ability-title refresh only. Persistent Tag state, Old View, Weapon mechanics, Probable execution policy, grid/layout, typography, colors, Cards, Waha, FIX mode, CSV data, and Version controls are unchanged.
  -->

'''
marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.146\n"
if text.count(marker) != 1:
    raise SystemExit("V31.146 change-note insertion marker missing")
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

# Focused Phase 2 acceptance checks.
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing after writeback")
final_view = html.unescape(vm.group(2))

for expected in [
    "if(!refreshNewViewAfterTagMutation())syncWeaponLayout();",
    "function refreshNewViewAfterTagMutation(){",
    "function toggleNewViewAbilityTag(key,tag){",
    "function toggleNewViewWeaponTag(weaponIndex,tagIndex){",
    "function toggleBoyzNewViewWeaponTag(weaponId,tagIndex){",
]:
    if expected not in final_view:
        raise SystemExit("V31.147 New View acceptance failed: " + expected)

for expected in [
    "function getAlternateViewEffectiveUnitStats(entry, unit, roster, fallbackStats = {}) {",
    "abilityTagStates: JSON.parse(JSON.stringify(entry.abilityTagStates || {}))",
    "getStructuredTagDefinitionEffect(assignment.tag, assignment.category);",
    'if (!["STAT", "UNIT_STAT"].includes(effectType) || target !== "UNIT") return;',
    "setRosterEntryAbilityTagState(",
    "projectedEntry,",
    "const profile = getEffectiveUnitProfile(projectedEntry, unit, roster);",
    "? getAlternateViewEffectiveUnitStats(entry, unit, roster, baseStats)",
    "<title>WH40k 11th V31.147</title>",
    "The current baseline is WH40k_11th_V31.147;",
    'const APP_VERSION = "31.147";',
    "version: 'V31.147',",
    "CHANGE NOTE - WH40k_11th_V31.147",
]:
    if expected not in text:
        raise SystemExit("V31.147 release acceptance failed: " + expected)

# Explicitly protect Phase 2 boundaries.
helper_start = text.find("    function getAlternateViewEffectiveUnitStats(")
helper_end = text.find(parent_marker, helper_start)
if helper_start < 0 or helper_end < 0:
    raise SystemExit("V31.147 helper bounds missing")
helper_body = text[helper_start:helper_end]
for forbidden in [
    "renderProbablePanel(",
    "refreshProbableSection(",
    "derivedWeaponAbilities",
    "getRosterEntryEffectiveWeaponProfile(",
]:
    if forbidden in helper_body:
        raise SystemExit("V31.147 Phase 2 scope violation: " + forbidden)

path.write_text(text, encoding="utf-8")
print("Built V31.147: active New View Abilities gate structured Unit-stat effects")
