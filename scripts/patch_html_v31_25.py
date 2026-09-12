from pathlib import Path
import re

source = Path("versions/WH40k_11th_V31.24.html")
path = Path("WH40k_11th.html")
text = source.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    text = text.replace(old, new, 1)


# Sequential release metadata.
replace_once('<title>WH40k 11th V31.24</title>', '<title>WH40k 11th V31.25</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.24;', 'The current baseline is WH40k_11th_V31.25;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.24";', 'const APP_VERSION = "31.25";', 'APP_VERSION')
replace_once("version: 'V31.24',", "version: 'V31.25',", 'InternalQuality version')

# Canonical Unit-level Tags do not belong under the source Ability's Melee/Range
# sections. Keep the assignment and its interactive state, but render the badge at
# the Unit-level tag line instead.
old_scoped_assignment = '''      getAbilityProtectedModifierTagAssignments(ability).forEach(assignment => {
        const definition = getTagDefinitionByTagAndCategory(assignment.tag, assignment.category);
        const scope = getTagDefinitionWeaponScope(definition, assignment.category).kind;
        const badge = renderProtectedAbilityTagBadge(
          assignment.tag,
          tagContext ? { ...tagContext, ability, category: assignment.category } : { ability, category: assignment.category }
        );'''
new_scoped_assignment = '''      getAbilityProtectedModifierTagAssignments(ability).forEach(assignment => {
        const definition = getTagDefinitionByTagAndCategory(assignment.tag, assignment.category);
        if (isUnitLevelTagDefinition(definition)) return;
        const scope = getTagDefinitionWeaponScope(definition, assignment.category).kind;
        const badge = renderProtectedAbilityTagBadge(
          assignment.tag,
          tagContext ? { ...tagContext, ability, category: assignment.category } : { ability, category: assignment.category }
        );'''
replace_once(old_scoped_assignment, new_scoped_assignment, 'remove Unit Tags from Ability-level rendering')

old_unit_level_block = '''    function isUnitNameLevelFnpAbility(ability) {
      const id = normalizeLookupId(ability && (ability.abilityId || ability.id || ""));
      const name = String(ability && (ability.name || ability.abilityName || "") || "").trim().toUpperCase();
      return /^FEEL_NO_PAIN_[456]$/.test(id)
        || /^FNP [456]\\+$/.test(name)
        || /^FEEL NO PAIN [456]\\+$/.test(name);
    }

    function getUnitNameLevelAbilities(unit) {
      return getCoreAbilitiesForUnit(unit).filter(ability => ability && !ability.isMissingLink && isUnitNameLevelFnpAbility(ability));
    }

    function renderUnitOtherAbilityTags(unit) {
      const tags = renderOtherAbilityTags(getUnitNameLevelAbilities(unit));
      return tags ? `<div class="unit-other-ability-tags">${tags}</div>` : "";
    }

    function renderUnitOtherAbilityLine(unit, className = "") {
      const tagsHtml = renderUnitOtherAbilityTags(unit);
      if (!tagsHtml) return "";
      const classes = ["unit-other-ability-line", className].filter(Boolean).join(" ");
      return `<div class="${classes}">${tagsHtml}</div>`;
    }'''
new_unit_level_block = '''    function isUnitNameLevelFnpAbility(ability) {
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

    function getRosterEntryUnitLevelStructuredTagRecords(entry, unit, roster = getDisplayedRosterForRosterScreen()) {
      if (!entry || !unit) return [];
      const recordsByTag = new Map();
      getRosterEntryAbilityTagSourceRecords(entry, unit, roster).forEach(record => {
        const ability = record && record.ability;
        if (!ability || ability.isMissingLink) return;
        getAbilityProtectedModifierTagAssignments(ability).forEach(assignment => {
          const definition = getTagDefinitionByTagAndCategory(assignment.tag, assignment.category);
          if (!isUnitLevelTagDefinition(definition)) return;
          const tagKey = normalizeAbilityTagPickerKey(getAbilityTagDisplayLabel(assignment.tag));
          if (!tagKey) return;
          const candidate = {
            ability,
            tag: assignment.tag,
            category: assignment.category,
            defaultOn: record.defaultOn !== false,
            isOn: getRosterEntryAbilityTagState(entry, ability, assignment.tag, record.defaultOn !== false, assignment.category)
          };
          const existing = recordsByTag.get(tagKey);
          if (!existing || (!existing.isOn && candidate.isOn)) recordsByTag.set(tagKey, candidate);
        });
      });
      return Array.from(recordsByTag.values());
    }

    function renderRosterEntryUnitLevelStructuredTags(entry, unit) {
      if (!entry || !unit) return "";
      return getRosterEntryUnitLevelStructuredTagRecords(entry, unit)
        .map(record => renderProtectedAbilityTagBadge(record.tag, {
          entry,
          ability: record.ability,
          category: record.category,
          defaultOn: record.defaultOn
        }))
        .join("");
    }

    function renderUnitOtherAbilityTags(unit, entry = null) {
      const coreTags = renderOtherAbilityTags(getUnitNameLevelAbilities(unit));
      const structuredTags = renderRosterEntryUnitLevelStructuredTags(entry, unit);
      const tags = [coreTags, structuredTags].filter(Boolean).join("");
      return tags ? `<div class="unit-other-ability-tags">${tags}</div>` : "";
    }

    function renderUnitOtherAbilityLine(unit, className = "", entry = null) {
      const tagsHtml = renderUnitOtherAbilityTags(unit, entry);
      if (!tagsHtml) return "";
      const classes = ["unit-other-ability-line", className].filter(Boolean).join(" ");
      return `<div class="${classes}">${tagsHtml}</div>`;
    }'''
replace_once(old_unit_level_block, new_unit_level_block, 'generic Unit-level structured Tag rendering')

replace_once(
    '${renderUnitOtherAbilityLine(unit, "view-edit-unit-other-ability-line view-edit-stats-tags-row")}',
    '${renderUnitOtherAbilityLine(unit, "view-edit-unit-other-ability-line view-edit-stats-tags-row", entry)}',
    'Edit Unit-level Tag call site'
)
replace_once(
    'const otherAbilityHtml = renderUnitOtherAbilityLine(unit, "view-unit-other-ability-line");',
    'const otherAbilityHtml = renderUnitOtherAbilityLine(unit, "view-unit-other-ability-line", entry);',
    'View Unit-level Tag call site'
)

# Preserve the canonical placement rule explicitly for future maintenance.
maintenance_anchor = '''    Version-switching invariant: Update and retained-version buttons must not be blocked by viewEditRosterDraftDirty or require a separate manual roster Save. The version host's existing prepare/checkpoint path persists the live roster state before mounting the next app runtime. Storage-not-ready protection remains valid.
'''
maintenance_replacement = maintenance_anchor + '''
    Unit-level structured Tag invariant: a Tag definition whose canonical Target or Affects is UNIT (or whose canonical Category is Unit-level) renders on the Unit-level tag line alongside Unit rules such as FNP, not inside the source Ability's Melee/Range Tag sections. The Unit-level badge keeps the source assignment's interactive on/off state. Weapon-scoped Tags remain on the source Ability and applicable Weapon profiles.
'''
replace_once(maintenance_anchor, maintenance_replacement, 'Unit-level Tag maintenance invariant')

# Add the new detailed release note and keep only the five newest detailed notes.
note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.24\n"
if note_marker not in text:
    raise SystemExit("release note insertion marker missing")
new_note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.25
    Scope: Promote canonical Unit-level structured Tags from Ability rows to the Unit-level tag line. Tags such as DEEP STRIKE now appear alongside Unit-level rules such as FNP while weapon-scoped Tags such as IGNORES COVER remain under their Melee/Range Ability sections. Unit-level structured badges preserve their original source Tag on/off state.
    Risk areas: Unit-level tag presentation and Ability structured-Tag placement. Weapon-scoped Tag behavior, derived Weapon rules, Probable, and Edit tag management remain unchanged.
  -->

'''
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.20\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f"old release note removal: expected 1 match, found {removed}")

checks = [
    '<title>WH40k 11th V31.25</title>',
    'const APP_VERSION = "31.25";',
    "version: 'V31.25',",
    'CHANGE NOTE - WH40k_11th_V31.25',
    'function isUnitLevelTagDefinition(definition)',
    'function getRosterEntryUnitLevelStructuredTagRecords(entry, unit',
    'if (isUnitLevelTagDefinition(definition)) return;',
    'renderUnitOtherAbilityLine(unit, "view-unit-other-ability-line", entry)',
    'Unit-level structured Tag invariant:',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))
if old_scoped_assignment in text:
    raise SystemExit('Unit-level Tags are still rendered inside Ability scope groups')
if old_unit_level_block in text:
    raise SystemExit('FNP-only Unit-level renderer still present')

path.write_text(text, encoding="utf-8")
print("Built WH40k_11th.html as V31.25 with Unit-level structured Tags")
