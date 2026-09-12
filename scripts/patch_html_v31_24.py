from pathlib import Path
import re

source = Path("versions/WH40k_11th_V31.23.html")
path = Path("WH40k_11th.html")
text = source.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    text = text.replace(old, new, 1)


# Sequential release metadata.
replace_once('<title>WH40k 11th V31.23</title>', '<title>WH40k 11th V31.24</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.23;', 'The current baseline is WH40k_11th_V31.24;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.23";', 'const APP_VERSION = "31.24";', 'APP_VERSION')
replace_once("version: 'V31.23',", "version: 'V31.24',", 'InternalQuality version')

# Version changes must not be blocked merely because Edit has unsaved roster changes.
# The existing WH40kPrepareVersionChange checkpoint already snapshots the live roster
# state into IndexedDB before the next runtime is mounted, so requiring a separate
# manual Save here is unnecessary and creates an unwanted UI blocker.
old_guard = '''    function canReloadAppVersion() {
      if (!appStorageInitialized) {
        setVersionHistoryStatus("Wait for the app to finish loading before changing versions.", "error", true);
        return false;
      }
      if (appEditMode && viewEditRosterDraftDirty) {
        setVersionHistoryStatus("Save roster changes before changing app versions.", "error", true);
        return false;
      }
      return true;
    }'''
new_guard = '''    function canReloadAppVersion() {
      if (!appStorageInitialized) {
        setVersionHistoryStatus("Wait for the app to finish loading before changing versions.", "error", true);
        return false;
      }
      return true;
    }'''
replace_once(old_guard, new_guard, 'remove manual roster-save version blocker')

# Preserve the intended contract explicitly for future maintenance.
maintenance_anchor = '''    View-mode Ability ordering invariant: Ability-table items whose effective order is 8 or 9 do not render at all in View mode. Edit mode continues to render them, including their order controls, so they remain manageable and can be moved back into visible orders 0-7.
'''
maintenance_replacement = maintenance_anchor + '''
    Version-switching invariant: Update and retained-version buttons must not be blocked by viewEditRosterDraftDirty or require a separate manual roster Save. The version host's existing prepare/checkpoint path persists the live roster state before mounting the next app runtime. Storage-not-ready protection remains valid.
'''
replace_once(maintenance_anchor, maintenance_replacement, 'version-switching maintenance invariant')

# Add the new detailed release note and keep only the five newest detailed notes.
note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.23\n"
if note_marker not in text:
    raise SystemExit("release note insertion marker missing")
new_note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.24
    Scope: Remove the manual roster-Save blocker from app version switching. Update and retained-version buttons can now change versions while Edit has dirty roster state; the existing version-change checkpoint persists the live state before the next runtime mounts.
    Risk areas: Version switching only. Storage-not-ready protection remains, and roster/version checkpoint persistence is otherwise unchanged.
  -->

'''
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.19\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f"old release note removal: expected 1 match, found {removed}")

checks = [
    '<title>WH40k 11th V31.24</title>',
    'const APP_VERSION = "31.24";',
    "version: 'V31.24',",
    'CHANGE NOTE - WH40k_11th_V31.24',
    'Version-switching invariant:',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))
if 'Save roster changes before changing app versions.' in text:
    raise SystemExit('manual roster-save version blocker text still present')
if 'if (appEditMode && viewEditRosterDraftDirty)' in text[text.find('function canReloadAppVersion()'):text.find('async function loadGithubVersion')]:
    raise SystemExit('dirty roster version blocker still present')

path.write_text(text, encoding="utf-8")
print("Built WH40k_11th.html as V31.24 without the manual roster-save version blocker")
