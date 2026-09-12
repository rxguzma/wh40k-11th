from pathlib import Path
import re

source = Path("versions/WH40k_11th_V31.34.html")
path = Path("WH40k_11th.html")
text = source.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    text = text.replace(old, new, 1)


# Sequential release metadata.
replace_once('<title>WH40k 11th V31.34</title>', '<title>WH40k 11th V31.35</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.34;', 'The current baseline is WH40k_11th_V31.35;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.34";', 'const APP_VERSION = "31.35";', 'APP_VERSION')
replace_once("version: 'V31.34',", "version: 'V31.35',", 'InternalQuality version')

# V31.35: only the user-approved compact Unit rules may move to the Unit-level
# line. Lone Operative has an explicit 3-inch variant. Invulnerable Save is
# intentionally excluded because it belongs in the profile/save presentation.
old_promoted_rules = '''      return key === "DEEP_STRIKE"
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
        || key.includes("_INVUL_");'''
new_promoted_rules = '''      return key === "DEEP_STRIKE"
        || key === "LONE_OPERATIVE"
        || key === "LONE_OPERATIVE_3"
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
        || key.startsWith("FEEL_NO_PAIN_");'''
replace_once(old_promoted_rules, new_promoted_rules, 'approved Unit-level rule list')

# Use one display path for Unit-level rules: structured Tags. Do not separately
# render the core Ability itself as another compact label. The direct core Ability
# remains a source record and its own structured Tag still renders normally.
old_unit_tag_renderer = '''    function renderUnitOtherAbilityTags(unit, entry = null) {
      const coreTags = renderOtherAbilityTags(getUnitNameLevelAbilities(unit));
      const structuredTags = renderRosterEntryUnitLevelStructuredTags(entry, unit);
      const tags = [coreTags, structuredTags].filter(Boolean).join("");
      return tags ? `<div class="unit-other-ability-tags">${tags}</div>` : "";
    }'''
new_unit_tag_renderer = '''    function renderUnitOtherAbilityTags(unit, entry = null) {
      const tags = renderRosterEntryUnitLevelStructuredTags(entry, unit);
      return tags ? `<div class="unit-other-ability-tags">${tags}</div>` : "";
    }'''
replace_once(old_unit_tag_renderer, new_unit_tag_renderer, 'single Unit-level structured Tag renderer')

old_invariant = '''    Unit-level compact-rule invariant: only Deep Strike, Lone Operative, Fights First, Stealth, Infiltrators, Scout 6\", Fight on Death, Invulnerable Save, and FNP are promoted to the Unit-level tag line. The same whitelist applies to direct core Abilities and to structured Tags carried by another Ability. An Ability carrying one of these promoted Tags defaults to order 8 so its source row does not render in View but remains manageable in Edit. All other Unit-affecting Tags remain with their source Ability.
'''
new_invariant = '''    Unit-level compact-rule invariant: only the approved structured Tags render on the Unit-level tag line: DEEP_STRIKE; LONE_OPERATIVE; LONE_OPERATIVE_3; FIGHTS_FIRST; STEALTH; INFILTRATORS; SCOUT_6 / SCOUTS_6; FIGHT_ON_DEATH and its explicit variants; and FNP / FEEL_NO_PAIN variants. Invulnerable Save is never promoted to this line. The Unit-level line renders from structured Tag assignments only; do not separately render a direct core Ability label for the same rule. An Ability carrying an approved Unit-level Tag defaults to order 8 so its source row does not render in View but remains manageable in Edit. All non-approved Tags remain with their source Ability.
'''
replace_once(old_invariant, new_invariant, 'approved Unit-level maintenance invariant')

# Add the new detailed release note and keep only the five newest detailed notes.
note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.34\n"
if note_marker not in text:
    raise SystemExit('release note insertion marker missing')
new_note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.35
    Scope: Make the Unit-level compact-rule line explicit and approval-driven. Only Deep Strike, Lone Op, Lone Op 3\", Fights First, Stealth, Infiltrators, Scout 6\", Fight on Death variants, and FNP variants can render there. Invulnerable Save is excluded. Unit-level rules now render through the structured Tag path only, so the core Ability label is not separately rendered as a second copy.
    Risk areas: Unit-level compact rule/tag placement only. Weapon/Ability filters, scoped Tags, Probable, Edit controls, and roster data are unchanged.
  -->

'''
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.30\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f'old release note removal: expected 1 match, found {removed}')

checks = [
    '<title>WH40k 11th V31.35</title>',
    'const APP_VERSION = "31.35";',
    "version: 'V31.35',",
    'CHANGE NOTE - WH40k_11th_V31.35',
    'key === "LONE_OPERATIVE_3"',
    'const tags = renderRosterEntryUnitLevelStructuredTags(entry, unit);',
    'Invulnerable Save is never promoted to this line.',
    'Unit-level line renders from structured Tag assignments only;',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))

promoted_fn = re.search(r'function isPromotedUnitRuleKey\(value\) \{(.*?)\n    \}', text, re.S)
if not promoted_fn:
    raise SystemExit('promoted Unit-rule helper missing after patch')
promoted_body = promoted_fn.group(1)
for forbidden in ('INVULNERABLE_SAVE', '_INVUL'):
    if forbidden in promoted_body:
        raise SystemExit(f'forbidden Unit-level promotion remains: {forbidden}')
if 'const coreTags = renderOtherAbilityTags(getUnitNameLevelAbilities(unit));' in text:
    raise SystemExit('direct core Ability Unit-line renderer still present')

path.write_text(text, encoding='utf-8')
print('Built WH40k_11th.html as V31.35 with approved Unit-level structured Tags')
