from pathlib import Path
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
replace_once("<title>WH40k 11th V31.147</title>", "<title>WH40k 11th V31.148</title>", "title")
replace_once(
    "The current baseline is WH40k_11th_V31.147;",
    "The current baseline is WH40k_11th_V31.148;",
    "baseline",
)
replace_once('const APP_VERSION = "31.147";', 'const APP_VERSION = "31.148";', "APP_VERSION")
replace_once("version: 'V31.147',", "version: 'V31.148',", "quality version")

# Phase 2 correction: Ability Active is the sole New View mechanical switch for
# Ability-owned Unit-stat Tags. Legacy Tag state / CSV Default_Active must not
# decide whether those Unit effects apply.
old_helper = r'''    function getAlternateViewEffectiveUnitStats(entry, unit, roster, fallbackStats = {}) {
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
new_helper = r'''    function getAlternateViewEffectiveUnitStats(entry, unit, roster, fallbackStats = {}) {
      if (!entry || !unit) return fallbackStats || {};

      // Work on a detached Tag-state projection. For Ability-owned Unit-stat
      // Tags, New View Ability Active is the only mechanical switch: Active
      // forces the Tag on; Inactive forces it off. Saved Tag state and CSV
      // Default_Active are therefore ignored for this New View calculation.
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
          const abilityActive = Boolean(
            itemKey && window.isAlternateViewAbilityMechanicallyEligible(entry.entryId, itemKey)
          );
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
              abilityActive,
              defaultOn,
              assignment.category
            );
          });
        });

      const profile = getEffectiveUnitProfile(projectedEntry, unit, roster);
      return profile && profile.stats ? profile.stats : (fallbackStats || {});
    };
'''
replace_once(old_helper, new_helper, "Ability-owned Unit-stat gate")

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.148
    Scope: Phase 2 correction for New View Ability-driven Unit mechanics. Ability Active is now the sole mechanical switch for structured STAT/UNIT_STAT Tags targeting UNIT that belong to that Ability. In the detached New View projection, an active Ability forces those Unit-stat Tags on and an inactive Ability forces them off, regardless of legacy per-Tag saved state or CSV Default_Active. The real roster Tag state is not mutated. Unit stats continue to refresh only for the open Unit. Weapon effects and Probable remain outside this phase.
    Risk areas: New View Unit-stat projection only. Old View, persistent Tag state, CSV data, Weapon mechanics, Probable execution, grid/layout, typography, colors, Cards, Waha, FIX mode, and Version controls are unchanged.
  -->

'''
marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.147\n"
if text.count(marker) != 1:
    raise SystemExit("V31.147 change-note insertion marker missing")
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

# Acceptance: the New View projection must force Unit-stat Tags from the Ability
# gate and must remain isolated from Weapon / Probable mechanics.
for expected in [
    "const abilityActive = Boolean(",
    "window.isAlternateViewAbilityMechanicallyEligible(entry.entryId, itemKey)",
    "assignment.tag,\n              abilityActive,",
    'if (!["STAT", "UNIT_STAT"].includes(effectType) || target !== "UNIT") return;',
    "const profile = getEffectiveUnitProfile(projectedEntry, unit, roster);",
    "<title>WH40k 11th V31.148</title>",
    "The current baseline is WH40k_11th_V31.148;",
    'const APP_VERSION = "31.148";',
    "version: 'V31.148',",
    "CHANGE NOTE - WH40k_11th_V31.148",
]:
    if expected not in text:
        raise SystemExit("V31.148 acceptance failed: " + expected)

helper_start = text.find("    function getAlternateViewEffectiveUnitStats(")
helper_end = text.find("    window.toggleAlternateViewAbilityTag = function(payload = {}) {", helper_start)
if helper_start < 0 or helper_end < 0:
    raise SystemExit("V31.148 helper bounds missing")
helper_body = text[helper_start:helper_end]
for forbidden in [
    "renderProbablePanel(",
    "refreshProbableSection(",
    "getRosterEntryEffectiveWeaponProfile(",
]:
    if forbidden in helper_body:
        raise SystemExit("V31.148 Phase 2 scope violation: " + forbidden)

path.write_text(text, encoding="utf-8")
print("Built V31.148: Ability Active alone gates New View Unit-stat Tags")
