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
replace_once("<title>WH40k 11th V31.148</title>", "<title>WH40k 11th V31.149</title>", "title")
replace_once(
    "The current baseline is WH40k_11th_V31.148;",
    "The current baseline is WH40k_11th_V31.149;",
    "baseline",
)
replace_once('const APP_VERSION = "31.148";', 'const APP_VERSION = "31.149";', "APP_VERSION")
replace_once("version: 'V31.148',", "version: 'V31.149',", "quality version")

# ---------------------------------------------------------------------------
# Phase 3: project Ability-owned WEAPON_STAT Tags through the existing effective
# Weapon profile engine. New View Ability Active is the sole mechanical switch.
# The detached projection never mutates saved roster Tag state.
# ---------------------------------------------------------------------------
parent_marker = '    window.toggleAlternateViewAbilityTag = function(payload = {}) {'
if text.count(parent_marker) != 1:
    raise SystemExit("V31.149 parent helper insertion marker missing")

weapon_helper = r'''    function getAlternateViewEffectiveWeaponStats(entry, unit, roster, weapon) {
      if (!entry || !unit || !weapon) return weapon || {};

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

            // Phase 3 is Weapon characteristic modifiers only. The existing
            // effective Weapon engine owns MELEE/RANGE scope matching and math.
            // Weapon rules, roll modifiers, rerolls, and Probable stay untouched.
            if (effectType !== "WEAPON_STAT" || !["MELEE", "RANGE"].includes(target)) return;

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

      return getRosterEntryEffectiveWeaponProfile(projectedEntry, unit, weapon, roster) || weapon;
    };

'''
text = text.replace(parent_marker, weapon_helper + parent_marker, 1)

# New View currently projects raw Weapon characteristics. Route those displayed
# A / BS-WS / S / AP / D values through the Phase 3 effective profile while
# retaining the exact existing Weapon rows, Tags, scope labels, and selection UI.
old_weapon_state_tail = r'''          const tagStates = tags.map(tag => {
            const locked = isInnateWeaponAbilityTag(weapon, tag);
            return {
              tag: String(tag || ""),
              active: locked ? true : getRosterEntryWeaponTagState(entry, weapon, tag, true),
              locked: Boolean(locked)
            };
          });
          return {'''
new_weapon_state_tail = r'''          const tagStates = tags.map(tag => {
            const locked = isInnateWeaponAbilityTag(weapon, tag);
            return {
              tag: String(tag || ""),
              active: locked ? true : getRosterEntryWeaponTagState(entry, weapon, tag, true),
              locked: Boolean(locked)
            };
          });
          const effectiveWeapon = entry && unit
            ? getAlternateViewEffectiveWeaponStats(entry, unit, roster, weapon)
            : weapon;
          return {'''
replace_once(old_weapon_state_tail, new_weapon_state_tail, "New View effective Weapon projection")

old_weapon_stats = r'''            attacks: String(weapon.attacks ?? ""),
            skill: String(weapon.skill ?? ""),
            strength: String(weapon.strength ?? ""),
            ap: String(weapon.ap ?? ""),
            damage: String(weapon.damage ?? ""),'''
new_weapon_stats = r'''            attacks: String(effectiveWeapon.attacks ?? weapon.attacks ?? ""),
            skill: String(effectiveWeapon.skill ?? weapon.skill ?? ""),
            strength: String(effectiveWeapon.strength ?? weapon.strength ?? ""),
            ap: String(effectiveWeapon.ap ?? weapon.ap ?? ""),
            damage: String(effectiveWeapon.damage ?? weapon.damage ?? ""),'''
replace_once(old_weapon_stats, new_weapon_stats, "New View effective Weapon stat fields")

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.149
    Scope: Phase 3 of New View Ability-driven mechanics. Ability Active is now the sole New View mechanical switch for Ability-owned structured WEAPON_STAT Tags targeting MELEE or RANGE. Active Abilities force those Weapon-stat Tags on and inactive Abilities force them off in a detached per-Unit projection, ignoring legacy per-Tag saved state and CSV Default_Active without mutating the real roster. New View Weapon A, BS/WS, S, AP, and D now come from the existing effective Weapon profile engine, which retains its existing MELEE/RANGE scope matching. Ability activation continues to refresh only the open Unit through the existing Unit-scoped path. Unit-stat behavior from V31.148 is unchanged. Weapon rules, roll modifiers, rerolls, and Probable execution are outside this phase and unchanged.
    Risk areas: New View Weapon characteristic projection only. Old View, persistent Tag state, CSV data, Unit-stat mechanics, Probable execution, grid/layout, typography, colors, Weapon/Ability selection UI, Cards, Waha, FIX mode, and Version controls are unchanged.
  -->

'''
marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.148\n"
if text.count(marker) != 1:
    raise SystemExit("V31.148 change-note insertion marker missing")
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

# Focused Phase 3 acceptance checks.
for expected in [
    "function getAlternateViewEffectiveWeaponStats(entry, unit, roster, weapon) {",
    'if (effectType !== "WEAPON_STAT" || !["MELEE", "RANGE"].includes(target)) return;',
    "window.isAlternateViewAbilityMechanicallyEligible(entry.entryId, itemKey)",
    "assignment.tag,\n              abilityActive,",
    "return getRosterEntryEffectiveWeaponProfile(projectedEntry, unit, weapon, roster) || weapon;",
    "const effectiveWeapon = entry && unit",
    "attacks: String(effectiveWeapon.attacks ?? weapon.attacks ?? \"\"),",
    "skill: String(effectiveWeapon.skill ?? weapon.skill ?? \"\"),",
    "strength: String(effectiveWeapon.strength ?? weapon.strength ?? \"\"),",
    "ap: String(effectiveWeapon.ap ?? weapon.ap ?? \"\"),",
    "damage: String(effectiveWeapon.damage ?? weapon.damage ?? \"\"),",
    "function getAlternateViewEffectiveUnitStats(entry, unit, roster, fallbackStats = {}) {",
    "<title>WH40k 11th V31.149</title>",
    "The current baseline is WH40k_11th_V31.149;",
    'const APP_VERSION = "31.149";',
    "version: 'V31.149',",
    "CHANGE NOTE - WH40k_11th_V31.149",
]:
    if expected not in text:
        raise SystemExit("V31.149 acceptance failed: " + expected)

helper_start = text.find("    function getAlternateViewEffectiveWeaponStats(")
helper_end = text.find(parent_marker, helper_start)
if helper_start < 0 or helper_end < 0:
    raise SystemExit("V31.149 Weapon helper bounds missing")
helper_body = text[helper_start:helper_end]
for forbidden in [
    "renderProbablePanel(",
    "refreshProbableSection(",
    "ROLL_MODIFIER",
    "REROLL",
    "WEAPON_RULE",
]:
    if forbidden in helper_body:
        raise SystemExit("V31.149 Phase 3 scope violation: " + forbidden)

path.write_text(text, encoding="utf-8")
print("Built V31.149: Ability Active gates matching New View MELEE/RANGE Weapon-stat effects")
