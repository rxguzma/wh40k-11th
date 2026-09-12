from pathlib import Path
import re

source = Path("versions/WH40k_11th_V31.21.html")
path = Path("WH40k_11th.html")
text = source.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    text = text.replace(old, new, 1)


# Sequential release metadata.
replace_once('<title>WH40k 11th V31.21</title>', '<title>WH40k 11th V31.22</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.21;', 'The current baseline is WH40k_11th_V31.22;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.21";', 'const APP_VERSION = "31.22";', 'APP_VERSION')
replace_once("version: 'V31.21',", "version: 'V31.22',", 'InternalQuality version')

# View-mode structured Tags are grouped by their canonical Weapon scope so duplicate
# labels from Melee and Range categories are visibly distinguishable.
old_tag_render = '''    function renderAbilityShortDescriptionWithProtectedTags(ability, value, editable = false, tagContext = null) {
      const safeText = escapeHtml(String(value || ""));
      const rendered = editable
        ? `<span class="ability-inline-editable-text" contenteditable="true" spellcheck="false" onclick="event.stopPropagation();">${safeText}</span>`
        : safeText;

      if (editable) return rendered;

      const appendedTags = getAbilityProtectedModifierTagAssignments(ability)
        .map(assignment => renderProtectedAbilityTagBadge(
          assignment.tag,
          tagContext ? { ...tagContext, ability, category: assignment.category } : { ability, category: assignment.category }
        ))
        .join(" ");

      return appendedTags
        ? `${rendered}${rendered ? `<div class="ability-appended-tags">${appendedTags}</div>` : appendedTags}`
        : rendered;
    }'''
new_tag_render = '''    function renderAbilityShortDescriptionWithProtectedTags(ability, value, editable = false, tagContext = null) {
      const safeText = escapeHtml(String(value || ""));
      const rendered = editable
        ? `<span class="ability-inline-editable-text" contenteditable="true" spellcheck="false" onclick="event.stopPropagation();">${safeText}</span>`
        : safeText;

      if (editable) return rendered;

      const grouped = { melee: [], range: [], other: [] };
      getAbilityProtectedModifierTagAssignments(ability).forEach(assignment => {
        const definition = getTagDefinitionByTagAndCategory(assignment.tag, assignment.category);
        const scope = getTagDefinitionWeaponScope(definition, assignment.category).kind;
        const badge = renderProtectedAbilityTagBadge(
          assignment.tag,
          tagContext ? { ...tagContext, ability, category: assignment.category } : { ability, category: assignment.category }
        );
        if (scope === "melee") grouped.melee.push(badge);
        else if (scope === "range") grouped.range.push(badge);
        else grouped.other.push(badge);
      });

      const scopedSection = (label, badges) => badges.length
        ? `<div class="ability-tag-scope-section"><div class="ability-primary-name ability-tag-scope-title">${escapeHtml(label)}</div><div class="ability-tag-scope-badges">${badges.join(" ")}</div></div>`
        : "";
      const appendedTags = [
        scopedSection("Melee", grouped.melee),
        scopedSection("Range", grouped.range),
        grouped.other.length ? `<div class="ability-tag-scope-badges">${grouped.other.join(" ")}</div>` : ""
      ].join("");

      return appendedTags
        ? `${rendered}${rendered ? `<div class="ability-appended-tags">${appendedTags}</div>` : appendedTags}`
        : rendered;
    }'''
replace_once(old_tag_render, new_tag_render, 'scoped View Tag rendering')

# Active REROLL structured Tags already drive Probable. Promote the same active Tag
# into each applicable effective Weapon profile so the Weapon panel visibly shows
# the reroll rule on Melee or Range profiles according to canonical Tag scope.
old_probable_rule = '''        const probableRule = getProbableRuleDescriptorFromTagDefinition(definition, item.category);
        if (probableRule && probableRule.key === "hitModifier") {
          hitRollModifier += Number(probableRule.value || 0) || 0;
          return;
        }

        if (effectType === "WEAPON_RULE" || effectType === "RULE") {
          const label = getAbilityTagDisplayLabel(item.tag);
          const key = normalizeAbilityTagPickerKey(label);
          if (!label || derivedRuleKeys.has(key)) return;
          derivedRuleKeys.add(key);
          derivedRules.push(label);
        }'''
new_probable_rule = '''        const probableRule = getProbableRuleDescriptorFromTagDefinition(definition, item.category);
        if (probableRule && probableRule.key === "hitModifier") {
          hitRollModifier += Number(probableRule.value || 0) || 0;
          return;
        }

        if (probableRule && (probableRule.key === "rerollHits" || probableRule.key === "rerollWounds")) {
          const label = getAbilityTagDisplayLabel(item.tag);
          const key = normalizeAbilityTagPickerKey(label);
          if (!label || derivedRuleKeys.has(key)) return;
          derivedRuleKeys.add(key);
          derivedRules.push(label);
          return;
        }

        if (effectType === "WEAPON_RULE" || effectType === "RULE") {
          const label = getAbilityTagDisplayLabel(item.tag);
          const key = normalizeAbilityTagPickerKey(label);
          if (!label || derivedRuleKeys.has(key)) return;
          derivedRuleKeys.add(key);
          derivedRules.push(label);
        }'''
replace_once(old_probable_rule, new_probable_rule, 'reroll promotion to Weapon profiles')

# Rules injected into an effective Weapon by an active source Ability/Stratagem are
# derived display rules. Keep them On and non-interactive at Weapon level; their
# source Tag remains the control that removes them.
old_weapon_badge_state = '''          if (!appEditMode && entry && entry.entryId) {
            const innateTag = isInnateWeaponAbilityTag(weapon, ability);
            const isOn = innateTag ? true : getRosterEntryWeaponTagState(entry, itemKey, ability, true);
            const classes = `weapon-ability-badge weapon-view-tag-toggle ${isOn ? "tag-on" : "tag-off"}${innateTag ? " tag-locked" : ""}`;
            if (innateTag) {
              return `
                <span class="weapon-ability-wrap">
                  <span class="${escapeAttr(classes)}" aria-disabled="true" data-weapon-tag="${escapeAttr(ability)}" data-weapon-tag-entry-id="${escapeAttr(entry.entryId)}" data-weapon-tag-item-key="${escapeAttr(itemKey)}">${abilityNameHtml}</span>
                </span>
              `;
            }
            return `
              <span class="weapon-ability-wrap">
                <span class="${escapeAttr(classes)}" role="button" tabindex="0" aria-pressed="${isOn ? "true" : "false"}" data-weapon-tag="${escapeAttr(ability)}" data-weapon-tag-entry-id="${escapeAttr(entry.entryId)}" data-weapon-tag-item-key="${escapeAttr(itemKey)}" onclick="event.stopPropagation(); toggleRosterEntryWeaponTag(event, this)" onkeydown="if(event.key === 'Enter' || event.key === ' '){event.preventDefault(); toggleRosterEntryWeaponTag(event, this);}">${abilityNameHtml}</span>
              </span>
            `;
          }'''
new_weapon_badge_state = '''          if (!appEditMode && entry && entry.entryId) {
            const innateTag = isInnateWeaponAbilityTag(weapon, ability);
            const derivedTag = (effectiveWeapon.derivedWeaponAbilities || []).some(rule =>
              normalizeAbilityTagPickerKey(rule) === normalizeAbilityTagPickerKey(ability)
            );
            const lockedTag = innateTag || derivedTag;
            const isOn = lockedTag ? true : getRosterEntryWeaponTagState(entry, itemKey, ability, true);
            const classes = `weapon-ability-badge weapon-view-tag-toggle ${isOn ? "tag-on" : "tag-off"}${lockedTag ? " tag-locked" : ""}`;
            if (lockedTag) {
              return `
                <span class="weapon-ability-wrap">
                  <span class="${escapeAttr(classes)}" aria-disabled="true" data-weapon-tag="${escapeAttr(ability)}" data-weapon-tag-entry-id="${escapeAttr(entry.entryId)}" data-weapon-tag-item-key="${escapeAttr(itemKey)}">${abilityNameHtml}</span>
                </span>
              `;
            }
            return `
              <span class="weapon-ability-wrap">
                <span class="${escapeAttr(classes)}" role="button" tabindex="0" aria-pressed="${isOn ? "true" : "false"}" data-weapon-tag="${escapeAttr(ability)}" data-weapon-tag-entry-id="${escapeAttr(entry.entryId)}" data-weapon-tag-item-key="${escapeAttr(itemKey)}" onclick="event.stopPropagation(); toggleRosterEntryWeaponTag(event, this)" onkeydown="if(event.key === 'Enter' || event.key === ' '){event.preventDefault(); toggleRosterEntryWeaponTag(event, this);}">${abilityNameHtml}</span>
              </span>
            `;
          }'''
replace_once(old_weapon_badge_state, new_weapon_badge_state, 'derived Weapon rule lock')

# Preserve the scope/display relationship as a regression-sensitive invariant.
maintenance_anchor = '''    View-mode Weapon selection invariant: Weapon selection is single-select. Selecting one Weapon makes that Weapon Active and automatically mutes every other Weapon in that Unit's Weapon table. Tapping the Active Weapon again clears selection and restores every Weapon to Default. Muted is an automatic sibling state only and must not be restored as a manual carousel step.
'''
maintenance_replacement = maintenance_anchor + '''
    View-mode scoped Tag invariant: structured Ability-like Tags with canonical Melee or Range scope render under separate Melee and Range subtitles. When an active source Tag defines a reroll for a Weapon scope, the applicable effective Weapon profiles also display that reroll as a derived locked rule; the source Tag remains the only control for enabling or disabling it.
'''
replace_once(maintenance_anchor, maintenance_replacement, 'scoped Tag maintenance invariant')

# Add the new detailed release note and keep only the five newest detailed notes.
note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.21\n"
if note_marker not in text:
    raise SystemExit("release note insertion marker missing")
new_note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.22
    Scope: Separate View-mode structured Tags into Melee and Range sections using canonical Tag scope. Active hit/wound reroll Tags are now also promoted into each applicable effective Weapon profile as derived locked Weapon rules, while continuing to drive Probable through the same structured Tag definitions.
    Risk areas: View-mode Ability/Stratagem Tag presentation and derived Weapon ability display. Source Tag activation, canonical Melee/Range filtering, Weapon selection, and Probable lazy initialization remain unchanged.
  -->

'''
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.17\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f"old release note removal: expected 1 match, found {removed}")

checks = [
    '<title>WH40k 11th V31.22</title>',
    'const APP_VERSION = "31.22";',
    "version: 'V31.22',",
    'CHANGE NOTE - WH40k_11th_V31.22',
    'scopedSection("Melee", grouped.melee)',
    'scopedSection("Range", grouped.range)',
    'probableRule.key === "rerollHits" || probableRule.key === "rerollWounds"',
    'const derivedTag = (effectiveWeapon.derivedWeaponAbilities || []).some',
    'View-mode scoped Tag invariant:',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))
if old_tag_render in text:
    raise SystemExit('flat View Tag renderer still present')
if old_probable_rule in text:
    raise SystemExit('reroll promotion patch not applied')
if old_weapon_badge_state in text:
    raise SystemExit('derived Weapon rules are still independently interactive')

path.write_text(text, encoding="utf-8")
print("Built WH40k_11th.html as V31.22 with scoped Tags and rerolls on Weapon profiles")
