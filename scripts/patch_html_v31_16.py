from pathlib import Path
import re

source = Path("versions/WH40k_11th_V31.12.html")
path = Path("WH40k_11th.html")
text = source.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    text = text.replace(old, new, 1)


# Build strictly from the accepted V31.12 release.
replace_once('<title>WH40k 11th V31.12</title>', '<title>WH40k 11th V31.16</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.12;', 'The current baseline is WH40k_11th_V31.16;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.12";', 'const APP_VERSION = "31.16";', 'APP_VERSION')
replace_once("version: 'V31.12',", "version: 'V31.16',", 'InternalQuality version')

# Remove only the green outline from the Unit + panel. Other Unit detail sections
# keep their existing active-unit-detail-box styling.
replace_once(
    '<div class="subsection active-unit-detail-box" id="add-${index}">${renderRosterViewAddPanel(entry, unit)}</div>',
    '<div class="subsection" id="add-${index}">${renderRosterViewAddPanel(entry, unit)}</div>',
    'Unit + panel green outline'
)

# Add the new detailed release note and keep the five-note rolling history.
note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.12\n"
if note_marker not in text:
    raise SystemExit("release note insertion marker missing")
new_note = """  <!--
    CHANGE NOTE - WH40k_11th_V31.16
    Scope: Rebuild from the accepted V31.12 baseline and remove the green outline from the Unit + Enhancement/Stratagem panel only.
    Risk areas: Unit + panel border styling only. V31.12 layout, sizing, eligibility, selection behavior, and unrelated roster UI are unchanged.
  -->

"""
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.8\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f"old release note removal: expected 1 match, found {removed}")

checks = [
    '<title>WH40k 11th V31.16</title>',
    'const APP_VERSION = "31.16";',
    "version: 'V31.16',",
    'CHANGE NOTE - WH40k_11th_V31.16',
    '<div class="subsection" id="add-${index}">${renderRosterViewAddPanel(entry, unit)}</div>'
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))

path.write_text(text, encoding="utf-8")
print("Rebuilt WH40k_11th.html as V31.16 from V31.12 and removed the Unit + panel green outline")
