from pathlib import Path
import re

source = Path("versions/WH40k_11th_V31.20.html")
path = Path("WH40k_11th.html")
text = source.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    text = text.replace(old, new, 1)


# Sequential release metadata.
replace_once('<title>WH40k 11th V31.20</title>', '<title>WH40k 11th V31.21</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.20;', 'The current baseline is WH40k_11th_V31.21;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.20";', 'const APP_VERSION = "31.21";', 'APP_VERSION')
replace_once("version: 'V31.20',", "version: 'V31.21',", 'InternalQuality version')

# View-mode Weapon selection is now single-select. Selecting a Weapon automatically
# mutes every sibling Weapon. Selecting the active Weapon again clears the selection
# and returns every Weapon to Default. Muted is no longer a manual carousel state.
old_weapon_cycle = '''    function cycleViewRosterWeaponRowState(row) {
      if (appEditMode || !row || !row.matches("[data-view-roster-weapon-kind]")) return;
      const currentState = String(row.dataset.viewRosterWeaponState || "default").trim().toLowerCase();
      const nextState = currentState === "default"
        ? "active"
        : currentState === "active"
          ? "inactive"
          : "default";
      const group = String(row.dataset.viewRosterWeaponGroup || "");
      const tbody = row.closest("tbody");
      const groupRows = group && tbody
        ? Array.from(tbody.querySelectorAll("[data-view-roster-weapon-group]")).filter(candidate => String(candidate.dataset.viewRosterWeaponGroup || "") === group)
        : [row];

      groupRows.forEach(candidate => {
        candidate.dataset.viewRosterWeaponState = nextState;
        candidate.classList.toggle("view-weapon-row-state-active", nextState === "active");
        candidate.classList.toggle("view-weapon-row-state-inactive", nextState === "inactive");
      });

      const entryId = String(row.dataset.probableEntryId || "").trim();
      const weaponKey = String(row.dataset.probableWeaponKey || "").trim();
      if (entryId && weaponKey) {
        if (nextState === "active") {
          viewProbableSelectedWeaponByEntry[entryId] = weaponKey;
        } else if (viewProbableSelectedWeaponByEntry[entryId] === weaponKey) {
          const replacement = Array.from(document.querySelectorAll(".view-weapon-main-row[data-probable-entry-id]"))
            .find(candidate => String(candidate.dataset.probableEntryId || "") === entryId && candidate.classList.contains("view-weapon-row-state-active"));
          if (replacement) viewProbableSelectedWeaponByEntry[entryId] = String(replacement.dataset.probableWeaponKey || "");
          else delete viewProbableSelectedWeaponByEntry[entryId];
        }
        refreshProbableSection(entryId);
      }
    }'''
new_weapon_cycle = '''    function cycleViewRosterWeaponRowState(row) {
      if (appEditMode || !row || !row.matches("[data-view-roster-weapon-kind]")) return;
      const group = String(row.dataset.viewRosterWeaponGroup || "");
      const tbody = row.closest("tbody");
      if (!group || !tbody) return;

      const currentState = String(row.dataset.viewRosterWeaponState || "default").trim().toLowerCase();
      const allWeaponRows = Array.from(tbody.querySelectorAll("[data-view-roster-weapon-group]"));
      const clearingSelection = currentState === "active";

      allWeaponRows.forEach(candidate => {
        const candidateGroup = String(candidate.dataset.viewRosterWeaponGroup || "");
        const nextState = clearingSelection
          ? "default"
          : candidateGroup === group
            ? "active"
            : "inactive";
        candidate.dataset.viewRosterWeaponState = nextState;
        candidate.classList.toggle("view-weapon-row-state-active", nextState === "active");
        candidate.classList.toggle("view-weapon-row-state-inactive", nextState === "inactive");
      });

      const entryId = String(row.dataset.probableEntryId || "").trim();
      const weaponKey = String(row.dataset.probableWeaponKey || "").trim();
      if (entryId) {
        if (!clearingSelection && weaponKey) viewProbableSelectedWeaponByEntry[entryId] = weaponKey;
        else delete viewProbableSelectedWeaponByEntry[entryId];
        refreshProbableSection(entryId);
      }
    }'''
replace_once(old_weapon_cycle, new_weapon_cycle, 'single-select Weapon state')

# Preserve this interaction as a regression-sensitive invariant.
maintenance_anchor = '''    Probable active-Tag invariant: combat mechanics are derived exclusively from currently active structured Tags. Short/Long Description text and saved/manual Probable mechanical overrides must never affect combat math. Numeric rule variants come from Tag Value and must not be enumerated in Probable. Unit/Target/Cover controls remain scenario inputs.
'''
maintenance_replacement = maintenance_anchor + '''
    View-mode Weapon selection invariant: Weapon selection is single-select. Selecting one Weapon makes that Weapon Active and automatically mutes every other Weapon in that Unit's Weapon table. Tapping the Active Weapon again clears selection and restores every Weapon to Default. Muted is an automatic sibling state only and must not be restored as a manual carousel step.
'''
replace_once(maintenance_anchor, maintenance_replacement, 'Weapon selection maintenance invariant')

# Add the new detailed release note and keep only the five newest detailed notes.
note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.20\n"
if note_marker not in text:
    raise SystemExit("release note insertion marker missing")
new_note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.21
    Scope: Change View-mode Weapon selection to single-select behavior. Selecting one Weapon automatically mutes every other Weapon in that Unit's Weapon table; tapping the selected Weapon again returns all Weapons to Default. Tapping an auto-muted Weapon switches the selection directly to it. Muted is no longer a manual Weapon carousel state.
    Risk areas: View-mode Weapon row selection state and Probable selected-Weapon handoff only. Ability row state cycling, Weapon filters, Weapon Tags, and Probable lazy initialization remain unchanged.
  -->

'''
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.16\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f"old release note removal: expected 1 match, found {removed}")

checks = [
    '<title>WH40k 11th V31.21</title>',
    'const APP_VERSION = "31.21";',
    "version: 'V31.21',",
    'CHANGE NOTE - WH40k_11th_V31.21',
    'const clearingSelection = currentState === "active";',
    'candidateGroup === group',
    'else delete viewProbableSelectedWeaponByEntry[entryId];',
    'Muted is an automatic sibling state only',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))
if old_weapon_cycle in text:
    raise SystemExit('old three-state Weapon carousel still present')

path.write_text(text, encoding="utf-8")
print("Built WH40k_11th.html as V31.21 with single-select Weapon behavior")
