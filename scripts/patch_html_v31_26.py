from pathlib import Path
import re

source = Path("versions/WH40k_11th_V31.25.html")
path = Path("WH40k_11th.html")
text = source.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    text = text.replace(old, new, 1)


def sub_once(pattern: str, replacement: str, label: str) -> None:
    global text
    text, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")


# Sequential release metadata.
replace_once('<title>WH40k 11th V31.25</title>', '<title>WH40k 11th V31.26</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.25;', 'The current baseline is WH40k_11th_V31.26;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.25";', 'const APP_VERSION = "31.26";', 'APP_VERSION')
replace_once("version: 'V31.25',", "version: 'V31.26',", 'InternalQuality version')

# Scoped structured Tags belong beside the Ability-like title in View, not in the
# description cell. Edit continues to show the existing Tag editor separately.
sub_once(
    r'''    function renderAbilityShortDescriptionWithProtectedTags\(ability, value, editable = false, tagContext = null\) \{.*?\n    \}\n\n    function renderAbilityDescriptionText''',
    '''    function renderAbilityShortDescriptionWithProtectedTags(ability, value, editable = false, tagContext = null) {
      const safeText = escapeHtml(String(value || ""));
      return editable
        ? `<span class="ability-inline-editable-text" contenteditable="true" spellcheck="false" onclick="event.stopPropagation();">${safeText}</span>`
        : safeText;
    }

    function renderAbilityDescriptionText''',
    'remove View Tags from descriptions'
)

# Reusable View title helpers. Canonical Unit-level Tags remain on the Unit tag line;
# weapon-scoped Tags are inline beside the title and follow the existing Range/Melee
# roster filter. Other non-Unit scopes remain inline and always visible.
helper_anchor = '''    function getAbilityProtectedModifierTags(ability) {
      return getAbilityProtectedModifierTagAssignments(ability).map(assignment => assignment.tag);
    }
'''
helper_block = helper_anchor + '''
    function getAbilityLikeTagSourceKey(sourceKind, sourceItem) {
      const kind = String(sourceKind || "ability").trim().toLowerCase() || "ability";
      if (!sourceItem) return "";
      if (kind === "enhancement") return getDetachmentEnhancementItemEditKey(sourceItem);
      if (kind === "detachment-rule") return getDetachmentRuleItemEditKey(sourceItem);
      if (kind === "stratagem") return getDetachmentStratagemItemEditKey(sourceItem);
      return getAbilityItemEditKey(getAbilitySourceItem(sourceItem) || sourceItem);
    }

    function renderAbilityTitleScopedTags(ability, tagContext = null) {
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
    }

    function renderAbilityLikeTitleScopedTags(sourceKind, sourceItem, entry, defaultOn = false) {
      if (!sourceItem) return "";
      const kind = String(sourceKind || "ability").trim().toLowerCase() || "ability";
      const ability = kind === "ability"
        ? sourceItem
        : (entry ? getRosterTaggedSourceAbility(kind, sourceItem, entry) : null);
      if (!ability) return "";
      return renderAbilityTitleScopedTags(ability, {
        entry,
        defaultOn: defaultOn !== false,
        sourceKind: kind,
        sourceKey: getAbilityLikeTagSourceKey(kind, sourceItem)
      });
    }

    function renderAbilityTitleNameHtml(nameHtml, titleTagsHtml = "", extraNameClass = "") {
      const safeNameHtml = String(nameHtml || "");
      const safeExtraClass = String(extraNameClass || "").trim();
      const nameClass = `ability-primary-name${safeExtraClass ? ` ${safeExtraClass}` : ""}`;
      const tags = String(titleTagsHtml || "");
      if (!tags) return `<span class="${escapeAttr(nameClass)}">${safeNameHtml}</span>`;
      return `<span class="ability-title-inline"><span class="${escapeAttr(nameClass)}">${safeNameHtml}</span><span class="ability-title-scoped-tags">${tags}</span></span>`;
    }
'''
replace_once(helper_anchor, helper_block, 'insert scoped title Tag helpers')

# Compact inline title layout; badges can wrap beside the title without creating a
# separate Melee/Range subtitle row.
css_anchor = '    .ability-name-cell { font-weight: 900; }\n'
css_block = css_anchor + '''    .ability-title-inline { display: flex; flex-wrap: wrap; align-items: center; gap: 4px; min-width: 0; }
    .ability-title-inline .ability-primary-name { display: inline; }
    .ability-title-scoped-tags { display: inline-flex; flex-wrap: wrap; align-items: center; gap: 3px; }
    .ability-title-scoped-tag { display: inline-flex; align-items: center; }
'''
replace_once(css_anchor, css_block, 'inline Ability title Tag CSS')

# The existing Range/Melee controls now also show/hide matching scoped title Tags.
old_sync = '''    function syncViewRosterWeaponRows() {
      if (appEditMode) return;
      document.querySelectorAll("[data-view-roster-weapon-kind]").forEach(row => {
        const kind = String(row.dataset.viewRosterWeaponKind || "").trim().toLowerCase();
        row.classList.toggle("hidden", !isViewRosterWeaponKindVisible(kind));
      });
    }'''
new_sync = '''    function syncViewRosterWeaponRows() {
      if (appEditMode) return;
      document.querySelectorAll("[data-view-roster-weapon-kind]").forEach(row => {
        const kind = String(row.dataset.viewRosterWeaponKind || "").trim().toLowerCase();
        row.classList.toggle("hidden", !isViewRosterWeaponKindVisible(kind));
      });
      document.querySelectorAll("[data-view-ability-tag-scope]").forEach(node => {
        const scope = String(node.dataset.viewAbilityTagScope || "").trim().toLowerCase();
        node.hidden = (scope === "range" || scope === "melee") && !isViewRosterWeaponKindVisible(scope);
      });
    }'''
replace_once(old_sync, new_sync, 'Range/Melee scoped Tag sync')

# Innate Ability title.
replace_once(
    '<td class="ability-name-cell"><span class="ability-primary-name">${renderSpreadsheetOverrideValue(safeRoster, itemKey, "name", escapeHtml(ability.name))}</span></td>',
    '<td class="ability-name-cell">${renderAbilityTitleNameHtml(renderSpreadsheetOverrideValue(safeRoster, itemKey, "name", escapeHtml(ability.name)), renderAbilityLikeTitleScopedTags("ability", ability, entry, defaultTagsOn))}</td>',
    'innate Ability inline title Tags'
)

# Selected Enhancement title.
replace_once(
    '<td class="ability-name-cell"><span class="ability-primary-name enhancement-detail-name">${nameHtml}</span></td>',
    '<td class="ability-name-cell">${renderAbilityTitleNameHtml(nameHtml, item ? renderAbilityLikeTitleScopedTags("enhancement", item, entry, getRosterTaggedSourceDefaultActive("enhancement", item)) : "", "enhancement-detail-name")}</td>',
    'selected Enhancement inline title Tags'
)

# Unit Detachment Rule title.
replace_once(
    '<td class="ability-name-cell"><span class="ability-primary-name">${nameHtml}</span></td>\n          <td class="ability-description-cell">${renderUnitAbilityDetachmentRuleDescription(item, roster, "", "", entry, getRosterTaggedSourceDefaultActive("detachment-rule", item))}</td>',
    '<td class="ability-name-cell">${renderAbilityTitleNameHtml(nameHtml, renderAbilityLikeTitleScopedTags("detachment-rule", item, entry, getRosterTaggedSourceDefaultActive("detachment-rule", item)))}</td>\n          <td class="ability-description-cell">${renderUnitAbilityDetachmentRuleDescription(item, roster, "", "", entry, getRosterTaggedSourceDefaultActive("detachment-rule", item))}</td>',
    'Detachment Rule inline title Tags'
)

# Unit Stratagem title.
replace_once(
    '<td class="ability-name-cell"><span class="ability-primary-name">${escapeHtml(selectedName)}</span></td>\n            <td class="ability-description-cell">${renderUnitAbilityStratagemDescription(selectedItem, roster, "", "", entry, getRosterTaggedSourceDefaultActive("stratagem", selectedItem))}</td>',
    '<td class="ability-name-cell">${renderAbilityTitleNameHtml(escapeHtml(selectedName), renderAbilityLikeTitleScopedTags("stratagem", selectedItem, entry, getRosterTaggedSourceDefaultActive("stratagem", selectedItem)))}</td>\n            <td class="ability-description-cell">${renderUnitAbilityStratagemDescription(selectedItem, roster, "", "", entry, getRosterTaggedSourceDefaultActive("stratagem", selectedItem))}</td>',
    'Stratagem inline title Tags'
)

# Propagated/sent item name cells keep provenance beneath the title line while Tags
# sit beside the title itself.
old_sent_name = '''    function renderRosterSentItemNameCell(resolved, roster, nameHtml, extraNameClass = "") {
      const safeNameHtml = String(nameHtml || "");
      const safeExtraClass = String(extraNameClass || "").trim();
      const nameClass = `ability-primary-name roster-sent-item-name${safeExtraClass ? ` ${safeExtraClass}` : ""}`;
      const provenance = renderRosterSentItemProvenance(resolved, roster);
      return `<td class="ability-name-cell roster-sent-item-name-cell"><span class="${escapeAttr(nameClass)}">${safeNameHtml}</span>${provenance}</td>`;
    }'''
new_sent_name = '''    function renderRosterSentItemNameCell(resolved, roster, nameHtml, extraNameClass = "", titleTagsHtml = "") {
      const safeExtraClass = String(extraNameClass || "").trim();
      const provenance = renderRosterSentItemProvenance(resolved, roster);
      const titleHtml = renderAbilityTitleNameHtml(nameHtml, titleTagsHtml, `roster-sent-item-name${safeExtraClass ? ` ${safeExtraClass}` : ""}`);
      return `<td class="ability-name-cell roster-sent-item-name-cell">${titleHtml}${provenance}</td>`;
    }'''
replace_once(old_sent_name, new_sent_name, 'sent item inline title Tag support')

replace_once(
    'const nameCell = renderRosterSentItemNameCell(resolved, safeRoster, nameHtml);',
    'const nameCell = renderRosterSentItemNameCell(resolved, safeRoster, nameHtml, "", renderAbilityLikeTitleScopedTags("ability", ability, entry, getRosterTaggedSourceDefaultActive("ability", ability)));',
    'sent Ability inline title Tags'
)

# Sent Enhancement / Detachment Rule / Stratagem branches.
replace_once(
    'const nameCell = renderRosterSentItemNameCell(resolved, roster, renderEnhancementReferenceName(item, roster), "enhancement-detail-name");',
    'const nameCell = renderRosterSentItemNameCell(resolved, roster, renderEnhancementReferenceName(item, roster), "enhancement-detail-name", renderAbilityLikeTitleScopedTags("enhancement", item, entry, getRosterTaggedSourceDefaultActive("enhancement", item)));',
    'sent Enhancement inline title Tags'
)
replace_once(
    'const nameCell = renderRosterSentItemNameCell(resolved, roster, renderDetachmentRuleReferenceName(item, roster));',
    'const nameCell = renderRosterSentItemNameCell(resolved, roster, renderDetachmentRuleReferenceName(item, roster), "", renderAbilityLikeTitleScopedTags("detachment-rule", item, entry, getRosterTaggedSourceDefaultActive("detachment-rule", item)));',
    'sent Detachment Rule inline title Tags'
)
replace_once(
    'const nameCell = renderRosterSentItemNameCell(resolved, roster, renderDetachmentStratagemReferenceName(item, roster));',
    'const nameCell = renderRosterSentItemNameCell(resolved, roster, renderDetachmentStratagemReferenceName(item, roster), "", renderAbilityLikeTitleScopedTags("stratagem", item, entry, getRosterTaggedSourceDefaultActive("stratagem", item)));',
    'sent Stratagem inline title Tags'
)

# Preserve the new compact/filter contract for future maintenance.
maintenance_anchor = '''    Unit-level structured Tag invariant: a Tag definition whose canonical Target or Affects is UNIT (or whose canonical Category is Unit-level) renders on the Unit-level tag line alongside Unit rules such as FNP, not inside the source Ability's Melee/Range Tag sections. The Unit-level badge keeps the source assignment's interactive on/off state. Weapon-scoped Tags remain on the source Ability and applicable Weapon profiles.
'''
maintenance_replacement = maintenance_anchor + '''
    View-mode scoped Ability Tag layout invariant: non-Unit structured Tags render inline beside their Ability-like title, never in separate Melee/Range subtitle rows beneath the description. Canonical Range and Melee scoped title Tags follow the existing global View Range/Melee filter immediately; if a weapon category is hidden, Tags for that category are hidden too. Unit-level Tags remain on the Unit-level tag line.
'''
replace_once(maintenance_anchor, maintenance_replacement, 'inline scoped Tag maintenance invariant')

# Add the new detailed release note and keep only the five newest detailed notes.
note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.25\n"
if note_marker not in text:
    raise SystemExit("release note insertion marker missing")
new_note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.26
    Scope: Move non-Unit structured Ability-like Tags from description-side Melee/Range sections into the title cell beside the Ability, Enhancement, Detachment Rule, or Stratagem name. Range- and Melee-scoped title Tags now follow the existing View Range/Melee weapon filter immediately, eliminating the extra subtitle/tag rows. Unit-level Tags remain promoted to the Unit-level tag line.
    Risk areas: View Ability-table title/tag layout and Range/Melee filter synchronization. Tag activation, Unit-level Tag promotion, derived Weapon rules, Probable, and Edit Tag management remain unchanged.
  -->

'''
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.21\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f"old release note removal: expected 1 match, found {removed}")

checks = [
    '<title>WH40k 11th V31.26</title>',
    'const APP_VERSION = "31.26";',
    "version: 'V31.26',",
    'CHANGE NOTE - WH40k_11th_V31.26',
    'function renderAbilityTitleScopedTags(ability, tagContext = null)',
    'data-view-ability-tag-scope=',
    'renderAbilityLikeTitleScopedTags("ability", ability, entry, defaultTagsOn)',
    'node.hidden = (scope === "range" || scope === "melee")',
    'View-mode scoped Ability Tag layout invariant:',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))
if 'ability-tag-scope-title' in text:
    raise SystemExit('old Melee/Range subtitle renderer still present')
if '<div class="ability-appended-tags">' in text:
    raise SystemExit('description-side Tag container still present')

path.write_text(text, encoding="utf-8")
print("Built WH40k_11th.html as V31.26 with inline scoped Ability Tags tied to Range/Melee filters")
