from pathlib import Path
import re

source = Path("versions/WH40k_11th_V31.27.html")
path = Path("WH40k_11th.html")
text = source.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    text = text.replace(old, new, 1)


# Sequential release metadata.
replace_once('<title>WH40k 11th V31.27</title>', '<title>WH40k 11th V31.28</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.27;', 'The current baseline is WH40k_11th_V31.28;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.27";', 'const APP_VERSION = "31.28";', 'APP_VERSION')
replace_once("version: 'V31.27',", "version: 'V31.28',", 'InternalQuality version')

# Put scoped Tags back with the description text, but keep the compact presentation:
# no Melee/Range subtitles. Canonical Unit-level Tags remain promoted to the Unit line.
old_description_renderer = '''    function renderAbilityShortDescriptionWithProtectedTags(ability, value, editable = false, tagContext = null) {
      const safeText = escapeHtml(String(value || ""));
      return editable
        ? `<span class="ability-inline-editable-text" contenteditable="true" spellcheck="false" onclick="event.stopPropagation();">${safeText}</span>`
        : safeText;
    }'''
new_description_renderer = '''    function renderAbilityShortDescriptionWithProtectedTags(ability, value, editable = false, tagContext = null) {
      const safeText = escapeHtml(String(value || ""));
      const rendered = editable
        ? `<span class="ability-inline-editable-text" contenteditable="true" spellcheck="false" onclick="event.stopPropagation();">${safeText}</span>`
        : safeText;
      if (editable) return rendered;

      const appendedTags = getAbilityProtectedModifierTagAssignments(ability).map(assignment => {
        const definition = getTagDefinitionByTagAndCategory(assignment.tag, assignment.category);
        if (isUnitLevelTagDefinition(definition)) return "";
        const scope = getTagDefinitionWeaponScope(definition, assignment.category).kind;
        const visible = scope === "melee" || scope === "range"
          ? isViewRosterWeaponKindVisible(scope)
          : true;
        const badge = renderProtectedAbilityTagBadge(
          assignment.tag,
          tagContext ? { ...tagContext, ability, category: assignment.category } : { ability, category: assignment.category }
        );
        if (!badge) return "";
        return `<span class="ability-description-scoped-tag" data-view-ability-tag-scope="${escapeAttr(scope)}"${visible ? "" : " hidden"}>${badge}</span>`;
      }).filter(Boolean).join(" ");

      return appendedTags
        ? `${rendered}${rendered ? ` <span class="ability-description-scoped-tags">${appendedTags}</span>` : `<span class="ability-description-scoped-tags">${appendedTags}</span>`}`
        : rendered;
    }'''
replace_once(old_description_renderer, new_description_renderer, 'restore description-side scoped Tags')

# Stop rendering scoped Tags in title cells. Keep the helper in place so existing call
# sites remain stable; it now intentionally returns no title badges.
old_title_renderer_start = '''    function renderAbilityTitleScopedTags(ability, tagContext = null) {
      if (!ability || appEditMode) return "";
      return getAbilityProtectedModifierTagAssignments(ability).map(assignment => {
        const definition = getTagDefinitionByTagAndCategory(assignment.tag, assignment.category);
        if (isUnitLevelTagDefinition(definition)) return "";
        const scope = getTagDefinitionWeaponScope(definition, assignment.category).kind;
        const visible = scope === "melee" || scope === "range"
          ? isViewRosterWeaponKindVisible(scope)
          : true;
        const badge = renderProtectedAbilityTagBadge(
          assignment.tag,
          tagContext ? { ...tagContext, ability, category: assignment.category } : { ability, category: assignment.category }
        );
        if (!badge) return "";
        return `<span class="ability-title-scoped-tag" data-view-ability-tag-scope="${escapeAttr(scope)}"${visible ? "" : " hidden"}>${badge}</span>`;
      }).filter(Boolean).join("");
    }'''
new_title_renderer = '''    function renderAbilityTitleScopedTags(ability, tagContext = null) {
      return "";
    }'''
replace_once(old_title_renderer_start, new_title_renderer, 'disable title-cell scoped Tags')

# Remove V31.27's title/tag layout pressure and add compact description-side spacing.
old_css = '''    .ability-title-inline { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: start; column-gap: 6px; min-width: 0; width: 100%; }
    .ability-title-inline .ability-primary-name { display: block; min-width: 0; }
    .ability-title-scoped-tags { display: inline-flex; flex-wrap: nowrap; align-items: center; gap: 3px; white-space: nowrap; justify-self: end; }
    .ability-title-scoped-tag { display: inline-flex; align-items: center; }
    .ability-title-scoped-tag .weapon-ability-badge { font-size: 0.72em; line-height: 1.05; padding: 3px 7px; }
'''
new_css = '''    .ability-title-inline { display: inline; }
    .ability-title-inline .ability-primary-name { display: inline; }
    .ability-title-scoped-tags { display: none; }
    .ability-description-scoped-tags { display: inline; white-space: normal; }
    .ability-description-scoped-tag { display: inline-flex; align-items: center; margin-left: 3px; vertical-align: middle; }
'''
replace_once(old_css, new_css, 'restore normal title width and description Tag CSS')

# The existing Range/Melee synchronization already targets data-view-ability-tag-scope,
# so the same top controls now drive description-side badges with no extra UI labels.
maintenance_anchor = '''    View-mode scoped Ability Tag layout invariant: non-Unit structured Tags render in the same title row beside their Ability-like title, never underneath the title and never in separate Melee/Range subtitle rows. The title can wrap within its own space, but the scoped Tag group remains top-aligned beside it. Canonical Range and Melee scoped title Tags follow the existing global View Range/Melee filter immediately; Range and Melee are controls only and must not be rendered as subtitles or labels in Ability rows. Unit-level Tags remain on the Unit-level tag line.
'''
maintenance_replacement = '''    View-mode scoped Ability Tag layout invariant: non-Unit structured Tags render with the Ability-like description text, not in the title cell and never in separate Melee/Range subtitle rows. Canonical Range and Melee scoped description Tags follow the existing global View Range/Melee filter immediately; Range and Melee are controls only and must not be rendered as subtitles or labels in Ability rows. Unit-level Tags remain on the Unit-level tag line.
'''
replace_once(maintenance_anchor, maintenance_replacement, 'description-side scoped Tag maintenance invariant')

# Add the new detailed release note and keep only the five newest detailed notes.
note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.27\n"
if note_marker not in text:
    raise SystemExit("release note insertion marker missing")
new_note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.28
    Scope: Move scoped structured Tags out of the Ability-like title cell and back into the description cell. Tags appear directly with the description text with no Melee/Range subtitles, while the existing top Range/Melee controls continue to drive scoped Tag visibility. This restores normal Ability-name width and prevents tags from squeezing long names.
    Risk areas: View Ability-like description/tag presentation only. Tag activation, Range/Melee filtering, Unit-level Tag promotion, Weapon rules, Probable, and Edit Tag management remain unchanged.
  -->

'''
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.23\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f"old release note removal: expected 1 match, found {removed}")

checks = [
    '<title>WH40k 11th V31.28</title>',
    'const APP_VERSION = "31.28";',
    "version: 'V31.28',",
    'CHANGE NOTE - WH40k_11th_V31.28',
    'ability-description-scoped-tag',
    'data-view-ability-tag-scope=',
    'function renderAbilityTitleScopedTags(ability, tagContext = null) {\n      return "";',
    'Range and Melee are controls only',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))
if 'ability-tag-scope-title' in text:
    raise SystemExit('Melee/Range subtitle renderer unexpectedly present')
if 'grid-template-columns: minmax(0, 1fr) auto' in text:
    raise SystemExit('V31.27 squeezing title grid still present')

path.write_text(text, encoding="utf-8")
print("Built WH40k_11th.html as V31.28 with scoped Tags in descriptions and no Range/Melee subtitles")
