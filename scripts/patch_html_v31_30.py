from pathlib import Path
import re

source = Path("versions/WH40k_11th_V31.29.html")
path = Path("WH40k_11th.html")
text = source.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    text = text.replace(old, new, 1)


# Sequential release metadata.
replace_once('<title>WH40k 11th V31.29</title>', '<title>WH40k 11th V31.30</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.29;', 'The current baseline is WH40k_11th_V31.30;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.29";', 'const APP_VERSION = "31.30";', 'APP_VERSION')
replace_once("version: 'V31.29',", "version: 'V31.30',", 'InternalQuality version')

# V31.29 generalized the promoted Unit-rule predicate, but the existing compact
# Unit badge renderer still calls this FNP-specific display helper. Restore the
# helper as a narrow label predicate so promoted core rules (including Deep Strike)
# render without throwing a ReferenceError.
anchor = '''    function getUnitNameLevelAbilities(unit) {
      return getCoreAbilitiesForUnit(unit).filter(ability => ability && !ability.isMissingLink && isUnitNameLevelAbility(ability));
    }
'''
replacement = '''    function isUnitNameLevelFnpAbility(ability) {
      if (!ability) return false;
      const id = normalizePromotedUnitRuleKey(ability.abilityId || ability.id || "");
      const name = normalizePromotedUnitRuleKey(ability.name || ability.abilityName || "");
      const isFnpKey = key => key === "FNP"
        || key.startsWith("FNP_")
        || key === "FEEL_NO_PAIN"
        || key.startsWith("FEEL_NO_PAIN_");
      return isFnpKey(id) || isFnpKey(name);
    }

    function getUnitNameLevelAbilities(unit) {
      return getCoreAbilitiesForUnit(unit).filter(ability => ability && !ability.isMissingLink && isUnitNameLevelAbility(ability));
    }
'''
replace_once(anchor, replacement, 'restore FNP compact-label helper')

maintenance_anchor = '''    Unit-level compact-rule invariant: only Deep Strike, Lone Operative, Fights First, Stealth, Infiltrators, Scout 6\", Fight on Death, Invulnerable Save, and FNP are promoted to the Unit-level tag line. The same whitelist applies to direct core Abilities and to structured Tags carried by another Ability. An Ability carrying one of these promoted Tags defaults to order 8 so its source row does not render in View but remains manageable in Edit. All other Unit-affecting Tags remain with their source Ability.
'''
maintenance_replacement = maintenance_anchor + '''    Compact Unit badge renderer invariant: renderOtherAbilityTags() still uses isUnitNameLevelFnpAbility() only to shorten Feel No Pain labels to FNP X+. Keep that helper available even though the broader promotion decision is owned by isUnitNameLevelAbility()/isPromotedUnitRuleKey(). Removing the FNP label helper causes promoted core-rule rendering to throw and can blank an opened Unit detail.
'''
replace_once(maintenance_anchor, maintenance_replacement, 'compact badge renderer maintenance invariant')

# Add the new detailed release note and keep only the five newest detailed notes.
note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.29\n"
if note_marker not in text:
    raise SystemExit("release note insertion marker missing")
new_note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.30
    Scope: Fix promoted Unit-level rule rendering after V31.29. Restore the FNP-specific compact-label helper still used by renderOtherAbilityTags so opening Units with promoted core rules such as Nazdreg's Deep Strike no longer throws a ReferenceError and blanks the Unit detail. The V31.29 whitelist and order-8 behavior are unchanged.
    Risk areas: Unit-level compact badge rendering only. Promotion whitelist, Ability ordering, scoped Tags, Weapon rules, Probable, and Edit controls remain unchanged.
  -->

'''
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.25\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f"old release note removal: expected 1 match, found {removed}")

checks = [
    '<title>WH40k 11th V31.30</title>',
    'const APP_VERSION = "31.30";',
    "version: 'V31.30',",
    'CHANGE NOTE - WH40k_11th_V31.30',
    'function isUnitNameLevelFnpAbility(ability)',
    'const label = isUnitNameLevelFnpAbility(ability) && fnpMatch',
    'Compact Unit badge renderer invariant:',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))

path.write_text(text, encoding="utf-8")
print("Built WH40k_11th.html as V31.30 with promoted Unit badge runtime fix")
