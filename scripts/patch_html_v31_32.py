from pathlib import Path
import re

source = Path("versions/WH40k_11th_V31.31.html")
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
replace_once('<title>WH40k 11th V31.31</title>', '<title>WH40k 11th V31.32</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.31;', 'The current baseline is WH40k_11th_V31.32;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.31";', 'const APP_VERSION = "31.32";', 'APP_VERSION')
replace_once("version: 'V31.31',", "version: 'V31.32',", 'InternalQuality version')

# The four-button filter is single-select. All is represented by no specific
# filter being active, so it is the default and automatically renders green.
old_state = 'viewRosterWeaponFilters = { range: true, melee: true };'
state_count = text.count(old_state)
if state_count < 1:
    raise SystemExit("weapon filter default state: expected at least 1 match")
text = text.replace(old_state, 'viewRosterWeaponFilters = { range: false, melee: false, other: false };')

old_sync_buttons = '''    function syncViewRosterWeaponFilterButtons() {
      document.querySelectorAll("[data-view-roster-weapon-filter]").forEach(button => {
        const key = String(button.dataset.viewRosterWeaponFilter || "").trim().toLowerCase();
        const active = key === "range"
          ? viewRosterWeaponFilters.range !== false
          : key === "melee"
            ? viewRosterWeaponFilters.melee !== false
            : false;
        button.classList.toggle("active", active);
        button.setAttribute("aria-pressed", active ? "true" : "false");
      });
    }'''
new_sync_buttons = '''    function getViewRosterWeaponFilterKey() {
      if (viewRosterWeaponFilters.range === true) return "range";
      if (viewRosterWeaponFilters.melee === true) return "melee";
      if (viewRosterWeaponFilters.other === true) return "other";
      return "all";
    }

    function syncViewRosterWeaponFilterButtons() {
      const selectedKey = getViewRosterWeaponFilterKey();
      document.querySelectorAll("[data-view-roster-weapon-filter]").forEach(button => {
        const key = String(button.dataset.viewRosterWeaponFilter || "").trim().toLowerCase();
        const active = key === selectedKey;
        button.classList.toggle("active", active);
        button.setAttribute("aria-pressed", active ? "true" : "false");
      });
    }'''
replace_once(old_sync_buttons, new_sync_buttons, 'four-state filter button sync')

old_visible = '''    function isViewRosterWeaponKindVisible(kind) {
      if (kind === "range") return viewRosterWeaponFilters.range !== false;
      if (kind === "melee") return viewRosterWeaponFilters.melee !== false;
      return true;
    }'''
new_visible = '''    function isViewRosterWeaponKindVisible(kind) {
      const selectedKey = getViewRosterWeaponFilterKey();
      const cleanKind = String(kind || "").trim().toLowerCase();
      if (selectedKey === "all") return true;
      if (selectedKey === "range" || selectedKey === "melee") return cleanKind === selectedKey;
      return cleanKind !== "range" && cleanKind !== "melee";
    }'''
replace_once(old_visible, new_visible, 'weapon kind visibility')

# Replace the V31.31 scoped-row sync. Specific filters now hide non-matching
# Ability rows rather than muting them. Mixed Range/Melee rows remain available
# in both relevant filters and show only Tags for the selected scope.
sub_once(
    r'''    function syncViewRosterWeaponRows\(\) \{.*?\n    \}(?=\n\n    function toggleViewRosterWeaponFilter)''',
    '''    function syncViewRosterWeaponRows() {
      if (appEditMode) return;
      const selectedKey = getViewRosterWeaponFilterKey();

      document.querySelectorAll("[data-view-roster-weapon-kind]").forEach(row => {
        const kind = String(row.dataset.viewRosterWeaponKind || "").trim().toLowerCase();
        row.classList.toggle("hidden", !isViewRosterWeaponKindVisible(kind));
      });

      document.querySelectorAll("[data-view-roster-ability-state]").forEach(row => {
        const scopedTagNodes = Array.from(row.querySelectorAll("[data-view-ability-tag-scope]"));
        const scopes = new Set(
          scopedTagNodes
            .map(node => String(node.dataset.viewAbilityTagScope || "").trim().toLowerCase())
            .filter(scope => scope === "range" || scope === "melee")
        );

        let visible = true;
        if (selectedKey === "range" || selectedKey === "melee") {
          visible = scopes.has(selectedKey);
        } else if (selectedKey === "other") {
          visible = scopes.size === 0;
        }

        row.classList.remove("view-ability-scope-muted");
        row.classList.toggle("hidden", !visible);

        scopedTagNodes.forEach(node => {
          const scope = String(node.dataset.viewAbilityTagScope || "").trim().toLowerCase();
          const hideTag = selectedKey !== "all"
            && (scope === "range" || scope === "melee")
            && scope !== selectedKey;
          node.classList.toggle("hidden", hideTag);
        });
      });
    }''',
    'four-state Weapon/Ability row sync'
)

# Radio-style behavior: selecting Range, Melee, or Other clears the other
# specific filters. All clears every specific filter.
sub_once(
    r'''    function toggleViewRosterWeaponFilter\(filterKey\) \{.*?\n    \}(?=\n\n    function renderViewRosterWeaponFilterButton)''',
    '''    function toggleViewRosterWeaponFilter(filterKey) {
      const key = String(filterKey || "").trim().toLowerCase();
      if (!["range", "melee", "other", "all"].includes(key)) return;

      viewRosterWeaponFilters.range = false;
      viewRosterWeaponFilters.melee = false;
      viewRosterWeaponFilters.other = false;
      if (key !== "all") viewRosterWeaponFilters[key] = true;

      syncViewRosterWeaponFilterButtons();
      syncViewRosterWeaponRows();
    }''',
    'single-select Range/Melee/Other/All filter'
)

old_render_button = '''    function renderViewRosterWeaponFilterButton(filterKey, label) {
      const key = String(filterKey || "").trim().toLowerCase();
      const active = key === "range"
        ? viewRosterWeaponFilters.range !== false
        : viewRosterWeaponFilters.melee !== false;
      return `<button type="button" class="view-roster-weapon-filter-button ${active ? "active" : ""}" data-view-roster-weapon-filter="${escapeAttr(key)}" aria-pressed="${active ? "true" : "false"}" onclick="event.stopPropagation(); toggleViewRosterWeaponFilter('${key}')">${escapeHtml(label)}</button>`;
    }'''
new_render_button = '''    function renderViewRosterWeaponFilterButton(filterKey, label) {
      const key = String(filterKey || "").trim().toLowerCase();
      const active = key === getViewRosterWeaponFilterKey();
      return `<button type="button" class="view-roster-weapon-filter-button ${active ? "active" : ""}" data-view-roster-weapon-filter="${escapeAttr(key)}" aria-pressed="${active ? "true" : "false"}" onclick="event.stopPropagation(); toggleViewRosterWeaponFilter('${key}')">${escapeHtml(label)}</button>`;
    }'''
replace_once(old_render_button, new_render_button, 'four-state filter button render')

old_header_buttons = '${renderViewRosterWeaponFilterButton("range", "Range")}${renderViewRosterWeaponFilterButton("melee", "Melee")}'
new_header_buttons = '${renderViewRosterWeaponFilterButton("range", "Range")}${renderViewRosterWeaponFilterButton("melee", "Melee")}${renderViewRosterWeaponFilterButton("other", "Other")}${renderViewRosterWeaponFilterButton("all", "All")}'
replace_once(old_header_buttons, new_header_buttons, 'Range Melee Other All header buttons')

# Scope filtering no longer uses the muted presentation introduced in V31.31.
old_mute_css = '''    .dark-table tr.view-ability-row-state-inactive,
    .dark-table tr[data-view-roster-ability-state="inactive"],
    .dark-table tr.view-ability-scope-muted {
      opacity: .38;
    }
'''
new_mute_css = '''    .dark-table tr.view-ability-row-state-inactive,
    .dark-table tr[data-view-roster-ability-state="inactive"] {
      opacity: .38;
    }
'''
replace_once(old_mute_css, new_mute_css, 'remove scope-muted CSS')

old_invariant = '''    View-mode scoped Ability Tag layout invariant: non-Unit structured Tags render with the Ability-like description text, not in the title cell and never in separate Melee/Range subtitle rows. Canonical Range and Melee scoped description Tags follow the existing global View Range/Melee filter immediately. Off-scope Tags are hidden with the app's .hidden class. An Ability-like row whose canonical scoped Tags are exclusively in the disabled scope remains visible but is muted; mixed Range+Melee rows stay normal and show only Tags for active scopes; unscoped rows remain normal. Range and Melee are controls only and must not be rendered as subtitles or labels in Ability rows. The Range/Melee controls support three reachable states: Range only, Melee only, and Both. Unit-level Tags remain on the Unit-level tag line.
'''
new_invariant = '''    View-mode Weapon/Ability filter invariant: the roster header controls are Range, Melee, Other, All in that order and are single-select. All is the default and is Active/green whenever Range, Melee, and Other are all off. Range shows Range Weapon rows and Ability-like rows carrying canonical Range-scoped Tags. Melee shows Melee Weapon rows and Ability-like rows carrying canonical Melee-scoped Tags. Other shows rows that are neither Range nor Melee, including unscoped Ability-like rows. All shows every Weapon and Ability-like row. Mixed Range+Melee Ability rows appear in both matching filters and show only the selected scope's Tags. Unit-level Tags remain on the Unit-level tag line.
'''
replace_once(old_invariant, new_invariant, 'four-state filter invariant')

# Add the new detailed release note and keep only the five newest detailed notes.
note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.31\n"
if note_marker not in text:
    raise SystemExit("release note insertion marker missing")
new_note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.32
    Scope: Replace the View roster Range/Melee carousel with a single-select Range | Melee | Other | All filter. All is the default and is green whenever no specific filter is selected. Range and Melee show their matching Weapon rows and scoped Ability rows; Other shows unscoped/non-Range/non-Melee rows; All restores every Weapon and Ability row.
    Risk areas: View roster header filter controls and View Weapon/Ability row visibility only. Weapon/Ability activation state, Tags, Probable, Edit mode, and roster data remain unchanged.
  -->

'''
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.27\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f"old release note removal: expected 1 match, found {removed}")

checks = [
    '<title>WH40k 11th V31.32</title>',
    'const APP_VERSION = "31.32";',
    "version: 'V31.32',",
    'CHANGE NOTE - WH40k_11th_V31.32',
    'function getViewRosterWeaponFilterKey()',
    'viewRosterWeaponFilters = { range: false, melee: false, other: false };',
    'renderViewRosterWeaponFilterButton("other", "Other")',
    'renderViewRosterWeaponFilterButton("all", "All")',
    'if (!["range", "melee", "other", "all"].includes(key)) return;',
    'visible = scopes.size === 0;',
    'row.classList.toggle("hidden", !visible);',
    'View-mode Weapon/Ability filter invariant:',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))
if 'viewRosterWeaponFilters = { range: true, melee: true };' in text:
    raise SystemExit('old Range/Melee default state still present')
if 'view-ability-scope-muted {' in text:
    raise SystemExit('scope-muted CSS still present')
if 'Range only, Melee only, and Both' in text:
    raise SystemExit('old three-state Range/Melee invariant still present')
if text.count('renderViewRosterWeaponFilterButton("other", "Other")') != 1:
    raise SystemExit('Other filter button count is not exactly one')
if text.count('renderViewRosterWeaponFilterButton("all", "All")') != 1:
    raise SystemExit('All filter button count is not exactly one')

path.write_text(text, encoding="utf-8")
print("Built WH40k_11th.html as V31.32 with Range | Melee | Other | All filtering")
