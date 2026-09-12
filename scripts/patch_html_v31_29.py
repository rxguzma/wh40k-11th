from pathlib import Path
import re

source = Path("versions/WH40k_11th_V31.28.html")
path = Path("WH40k_11th.html")
text = source.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    text = text.replace(old, new, 1)


# Sequential release metadata.
replace_once('<title>WH40k 11th V31.28</title>', '<title>WH40k 11th V31.29</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.28;', 'The current baseline is WH40k_11th_V31.29;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.28";', 'const APP_VERSION = "31.29";', 'APP_VERSION')
replace_once("version: 'V31.28',", "version: 'V31.29',", 'InternalQuality version')

# Replace V31.25's broad "any Unit tag" promotion with the explicit compact-rule
# whitelist. Direct core Abilities from this list and structured Tags carried by
# another Ability both render on the Unit-level line.
old_unit_helpers = '''    function isUnitNameLevelFnpAbility(ability) {
      const id = normalizeLookupId(ability && (ability.abilityId || ability.id || ""));
      const name = String(ability && (ability.name || ability.abilityName || "") || "").trim().toUpperCase();
      return /^FEEL_NO_PAIN_[456]$/.test(id)
        || /^FNP [456]\\+$/.test(name)
        || /^FEEL NO PAIN [456]\\+$/.test(name);
    }

    function getUnitNameLevelAbilities(unit) {
      return getCoreAbilitiesForUnit(unit).filter(ability => ability && !ability.isMissingLink && isUnitNameLevelFnpAbility(ability));
    }

    function isUnitLevelTagDefinition(definition) {
      if (!definition) return false;
      const target = String(definition.target || "").trim().toUpperCase();
      const affects = String(definition.affects || "").trim().toUpperCase();
      const category = String(definition.category || "").trim().toUpperCase();
      return target === "UNIT" || affects === "UNIT" || category === "UNIT" || category.startsWith("UNIT ");
    }
'''
new_unit_helpers = '''    function normalizePromotedUnitRuleKey(value) {
      return String(value || "")
        .trim()
        .toUpperCase()
        .replace(/[^A-Z0-9]+/g, "_")
        .replace(/^_+|_+$/g, "");
    }

    function isPromotedUnitRuleKey(value) {
      const key = normalizePromotedUnitRuleKey(value);
      if (!key) return false;
      return key === "DEEP_STRIKE"
        || key === "LONE_OPERATIVE"
        || key === "FIGHTS_FIRST"
        || key === "STEALTH"
        || key === "INFILTRATORS"
        || key === "SCOUT_6"
        || key === "SCOUTS_6"
        || key === "FIGHT_ON_DEATH"
        || key.startsWith("FIGHT_ON_DEATH_")
        || key === "FNP"
        || key.startsWith("FNP_")
        || key === "FEEL_NO_PAIN"
        || key.startsWith("FEEL_NO_PAIN_")
        || key === "INVULNERABLE_SAVE"
        || key.startsWith("INVULNERABLE_SAVE_")
        || key.endsWith("_INVUL")
        || key.includes("_INVUL_");
    }

    function isUnitNameLevelAbility(ability) {
      if (!ability) return false;
      return isPromotedUnitRuleKey(ability.abilityId || ability.id || "")
        || isPromotedUnitRuleKey(ability.name || ability.abilityName || "");
    }

    function getUnitNameLevelAbilities(unit) {
      return getCoreAbilitiesForUnit(unit).filter(ability => ability && !ability.isMissingLink && isUnitNameLevelAbility(ability));
    }

    function isPromotedUnitLevelTag(tag, definition) {
      if (isPromotedUnitRuleKey(tag)) return true;
      if (!definition) return false;
      return isPromotedUnitRuleKey(definition.tagId)
        || isPromotedUnitRuleKey(definition.id)
        || isPromotedUnitRuleKey(definition.displayTag)
        || isPromotedUnitRuleKey(definition.title);
    }

    function abilityHasPromotedUnitLevelRule(ability) {
      if (!ability) return false;
      if (isUnitNameLevelAbility(ability)) return true;
      return getAbilityProtectedModifierTagAssignments(ability).some(assignment => {
        const definition = getTagDefinitionByTagAndCategory(assignment.tag, assignment.category);
        return isPromotedUnitLevelTag(assignment.tag, definition);
      });
    }
'''
replace_once(old_unit_helpers, new_unit_helpers, 'compact Unit-rule whitelist helpers')

# The description renderer should keep only non-promoted Tags with the source
# Ability. Promoted compact Tags move to the Unit-level line.
replace_once(
    '        if (isUnitLevelTagDefinition(definition)) return "";',
    '        if (isPromotedUnitLevelTag(assignment.tag, definition)) return "";',
    'description-side promoted Tag exclusion'
)
replace_once(
    '          if (!isUnitLevelTagDefinition(definition)) return;',
    '          if (!isPromotedUnitLevelTag(assignment.tag, definition)) return;',
    'Unit-level structured Tag whitelist'
)

# Any Ability that is itself one of the compact rules, or carries one of those
# structured Tags, defaults to order 8. V31.23 already hides order 8/9 rows in View
# while keeping them available in Edit.
push_signature = 'const push = (orderKey, defaultOrder, render, probableEligible = true, sourceRef = null) => {'
if text.count(push_signature) != 1:
    raise SystemExit(f'Ability descriptor push signature: expected 1 match, found {text.count(push_signature)}')
text = text.replace(
    push_signature,
    push_signature + '\n        if (sourceRef && abilityHasPromotedUnitLevelRule(sourceRef)) defaultOrder = 8;',
    1
)

old_invariant = '''    Unit-level structured Tag invariant: a Tag definition whose canonical Target or Affects is UNIT (or whose canonical Category is Unit-level) renders on the Unit-level tag line alongside Unit rules such as FNP, not inside the source Ability's Melee/Range Tag sections. The Unit-level badge keeps the source assignment's interactive on/off state. Weapon-scoped Tags remain on the source Ability and applicable Weapon profiles.
'''
new_invariant = '''    Unit-level compact-rule invariant: only Deep Strike, Lone Operative, Fights First, Stealth, Infiltrators, Scout 6\", Fight on Death, Invulnerable Save, and FNP are promoted to the Unit-level tag line. The same whitelist applies to direct core Abilities and to structured Tags carried by another Ability. An Ability carrying one of these promoted Tags defaults to order 8 so its source row does not render in View but remains manageable in Edit. All other Unit-affecting Tags remain with their source Ability.
'''
replace_once(old_invariant, new_invariant, 'compact Unit-rule maintenance invariant')

# Add the new detailed release note and keep only the five newest detailed notes.
note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.28\n"
if note_marker not in text:
    raise SystemExit("release note insertion marker missing")
new_note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.29
    Scope: Restrict Unit-level compact rule promotion to Deep Strike, Lone Operative, Fights First, Stealth, Infiltrators, Scout 6\", Fight on Death, Invulnerable Save, and FNP. Direct core Abilities and structured Tags from this whitelist render at Unit level; unrelated Unit-affecting Tags stay with their source Ability. Any Ability carrying one of the promoted structured Tags defaults to order 8, keeping its source row out of View while preserving it in Edit.
    Risk areas: Unit-level compact rule placement and default Ability order for the promoted whitelist. Scoped description Tags, Weapon rules, Range/Melee filtering, Probable, and Edit controls remain unchanged.
  -->

'''
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.24\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f"old release note removal: expected 1 match, found {removed}")

checks = [
    '<title>WH40k 11th V31.29</title>',
    'const APP_VERSION = "31.29";',
    "version: 'V31.29',",
    'CHANGE NOTE - WH40k_11th_V31.29',
    'function isPromotedUnitRuleKey(value)',
    'key === "DEEP_STRIKE"',
    'key === "LONE_OPERATIVE"',
    'key === "FIGHTS_FIRST"',
    'key === "STEALTH"',
    'key === "INFILTRATORS"',
    'key === "SCOUTS_6"',
    'key.startsWith("FIGHT_ON_DEATH_")',
    'key.startsWith("FEEL_NO_PAIN_")',
    'key.startsWith("INVULNERABLE_SAVE_")',
    'function abilityHasPromotedUnitLevelRule(ability)',
    'if (sourceRef && abilityHasPromotedUnitLevelRule(sourceRef)) defaultOrder = 8;',
    'Unit-level compact-rule invariant:',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))
if 'function isUnitLevelTagDefinition(definition)' in text:
    raise SystemExit('broad Unit-level predicate still present')

path.write_text(text, encoding="utf-8")
print("Built WH40k_11th.html as V31.29 with compact Unit-rule whitelist")
