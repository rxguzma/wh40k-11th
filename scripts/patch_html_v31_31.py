from pathlib import Path
import re

source = Path("versions/WH40k_11th_V31.30.html")
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
replace_once('<title>WH40k 11th V31.30</title>', '<title>WH40k 11th V31.31</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.30;', 'The current baseline is WH40k_11th_V31.31;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.30";', 'const APP_VERSION = "31.31";', 'APP_VERSION')
replace_once("version: 'V31.30',", "version: 'V31.31',", 'InternalQuality version')

# Hidden scoped description badges must use the app's .hidden class. The previous
# hidden attribute was overridden by the badge display rule, so off-scope Tags could
# remain visible even when their Range/Melee filter was disabled.
old_tag_html = 'return `<span class="ability-description-scoped-tag" data-view-ability-tag-scope="${escapeAttr(scope)}"${visible ? "" : " hidden"}>${badge}</span>`;'
new_tag_html = 'return `<span class="ability-description-scoped-tag${visible ? "" : " hidden"}" data-view-ability-tag-scope="${escapeAttr(scope)}">${badge}</span>`;'
replace_once(old_tag_html, new_tag_html, 'scoped Tag hidden class')

# Reuse the existing muted visual language for scope-filtered Ability rows without
# changing the row's own saved/interactive Ability state.
old_mute_css = '''    .dark-table tr.view-ability-row-state-inactive,
    .dark-table tr[data-view-roster-ability-state="inactive"] {
      opacity: .38;
    }
'''
new_mute_css = '''    .dark-table tr.view-ability-row-state-inactive,
    .dark-table tr[data-view-roster-ability-state="inactive"],
    .dark-table tr.view-ability-scope-muted {
      opacity: .38;
    }
'''
replace_once(old_mute_css, new_mute_css, 'Ability scope mute CSS')

# Range/Melee now drives three things from one canonical state:
# 1) Weapon-row visibility, 2) scoped Tag visibility, 3) Ability-row muting.
old_sync = '''    function syncViewRosterWeaponRows() {
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
new_sync = '''    function syncViewRosterWeaponRows() {
      if (appEditMode) return;
      document.querySelectorAll("[data-view-roster-weapon-kind]").forEach(row => {
        const kind = String(row.dataset.viewRosterWeaponKind || "").trim().toLowerCase();
        row.classList.toggle("hidden", !isViewRosterWeaponKindVisible(kind));
      });

      const scopedTagNodes = Array.from(document.querySelectorAll("[data-view-ability-tag-scope]"));
      scopedTagNodes.forEach(node => {
        const scope = String(node.dataset.viewAbilityTagScope || "").trim().toLowerCase();
        const shouldHide = (scope === "range" || scope === "melee") && !isViewRosterWeaponKindVisible(scope);
        node.classList.toggle("hidden", shouldHide);
      });

      document.querySelectorAll("tr.view-ability-scope-muted").forEach(row => {
        row.classList.remove("view-ability-scope-muted");
      });

      const scopedRows = new Set(scopedTagNodes.map(node => node.closest("tr")).filter(Boolean));
      scopedRows.forEach(row => {
        const scopes = new Set(
          Array.from(row.querySelectorAll("[data-view-ability-tag-scope]"))
            .map(node => String(node.dataset.viewAbilityTagScope || "").trim().toLowerCase())
            .filter(scope => scope === "range" || scope === "melee")
        );
        if (!scopes.size) return;
        const hasVisibleScope = Array.from(scopes).some(scope => isViewRosterWeaponKindVisible(scope));
        row.classList.toggle("view-ability-scope-muted", !hasVisibleScope);
      });
    }'''
replace_once(old_sync, new_sync, 'Range/Melee scoped Ability sync')

# Make both Range+Melee reachable again. The two buttons form a three-state carousel:
# both -> one scope -> the other scope -> both. Tapping the sole active scope restores
# both; tapping the inactive scope switches directly to that scope.
sub_once(
    r'''    function toggleViewRosterWeaponFilter\(filterKey\) \{.*?\n    \}(?=\n\n    function renderViewRosterWeaponFilterButton)''',
    '''    function toggleViewRosterWeaponFilter(filterKey) {
      const key = String(filterKey || "").trim().toLowerCase();
      if (key !== "range" && key !== "melee") return;

      const otherKey = key === "range" ? "melee" : "range";
      const isCurrentlyActive = viewRosterWeaponFilters[key] !== false;
      const isOtherActive = viewRosterWeaponFilters[otherKey] !== false;

      if (isCurrentlyActive && isOtherActive) {
        // Both active: turn off the tapped scope and leave the other scope selected.
        viewRosterWeaponFilters[key] = false;
      } else if (isCurrentlyActive) {
        // Sole active scope: next carousel state is Both.
        viewRosterWeaponFilters[otherKey] = true;
      } else if (isOtherActive) {
        // One active + tapped inactive: switch directly to the tapped scope.
        viewRosterWeaponFilters[otherKey] = false;
        viewRosterWeaponFilters[key] = true;
      } else {
        // Defensive recovery: restore Both rather than leaving an all-off state.
        viewRosterWeaponFilters.range = true;
        viewRosterWeaponFilters.melee = true;
      }

      syncViewRosterWeaponFilterButtons();
      syncViewRosterWeaponRows();
    }''',
    'three-state Range/Melee carousel'
)

old_invariant = '''    View-mode scoped Ability Tag layout invariant: non-Unit structured Tags render with the Ability-like description text, not in the title cell and never in separate Melee/Range subtitle rows. Canonical Range and Melee scoped description Tags follow the existing global View Range/Melee filter immediately; Range and Melee are controls only and must not be rendered as subtitles or labels in Ability rows. Unit-level Tags remain on the Unit-level tag line.
'''
new_invariant = '''    View-mode scoped Ability Tag layout invariant: non-Unit structured Tags render with the Ability-like description text, not in the title cell and never in separate Melee/Range subtitle rows. Canonical Range and Melee scoped description Tags follow the existing global View Range/Melee filter immediately. Off-scope Tags are hidden with the app's .hidden class. An Ability-like row whose canonical scoped Tags are exclusively in the disabled scope remains visible but is muted; mixed Range+Melee rows stay normal and show only Tags for active scopes; unscoped rows remain normal. Range and Melee are controls only and must not be rendered as subtitles or labels in Ability rows. The Range/Melee controls support three reachable states: Range only, Melee only, and Both. Unit-level Tags remain on the Unit-level tag line.
'''
replace_once(old_invariant, new_invariant, 'scoped Ability filter invariant')

# Add the new detailed release note and keep only the five newest detailed notes.
note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.30\n"
if note_marker not in text:
    raise SystemExit("release note insertion marker missing")
new_note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.31
    Scope: Make the top Range/Melee controls drive scoped Ability presentation correctly. Off-scope description Tags now hide reliably, opposite-scope-only Ability rows remain visible but muted, mixed-scope rows stay normal and show only active-scope Tags, and unscoped rows remain unchanged. The Range/Melee control behavior now exposes all three states: Range only, Melee only, and Both.
    Risk areas: View Range/Melee filtering, scoped Ability-row presentation, and the Range/Melee button carousel only. Tag activation, Unit-level compact rules, Weapon selection state, Probable, and Edit controls remain unchanged.
  -->

'''
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.26\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f"old release note removal: expected 1 match, found {removed}")

checks = [
    '<title>WH40k 11th V31.31</title>',
    'const APP_VERSION = "31.31";',
    "version: 'V31.31',",
    'CHANGE NOTE - WH40k_11th_V31.31',
    'view-ability-scope-muted',
    'node.classList.toggle("hidden", shouldHide);',
    'const scopedRows = new Set(scopedTagNodes.map(node => node.closest("tr")).filter(Boolean));',
    'viewRosterWeaponFilters[otherKey] = true;',
    'Range only, Melee only, and Both',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))
if 'node.hidden = (scope === "range" || scope === "melee")' in text:
    raise SystemExit('old hidden-attribute scoped Tag filtering still present')
if 'class="ability-description-scoped-tag" data-view-ability-tag-scope=' in text:
    raise SystemExit('description scoped Tag renderer still lacks class-based initial hiding')

path.write_text(text, encoding="utf-8")
print("Built WH40k_11th.html as V31.31 with three-state Range/Melee scoped Ability behavior")
