from pathlib import Path
import re

path = Path("WH40k_11th.html")
text = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    text = text.replace(old, new, 1)


# Sequential release metadata.
replace_once('<title>WH40k 11th V31.11</title>', '<title>WH40k 11th V31.12</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.11;', 'The current baseline is WH40k_11th_V31.12;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.11";', 'const APP_VERSION = "31.12";', 'APP_VERSION')
replace_once("version: 'V31.11',", "version: 'V31.12',", 'InternalQuality version')

note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.11\n"
if note_marker not in text:
    raise SystemExit("release note insertion marker missing")
new_note = """  <!--
    CHANGE NOTE - WH40k_11th_V31.12
    Scope: Increase vertical padding on Unit + panel Enhancement/Stratagem option buttons so multi-line labels fit comfortably inside their boxes.
    Risk areas: Unit + panel option-button sizing only. Eligibility, selection behavior, and unrelated roster layout are unchanged.
  -->

"""
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.7\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f"old release note removal: expected 1 match, found {removed}")

# Give the three-column Unit + option buttons a little more vertical room.
replace_once(
    """    .view-edit-unit-add-option {
      min-width: 0;
      height: auto;
      padding: 9px 4px;
      line-height: 1.15;
      white-space: normal;
""",
    """    .view-edit-unit-add-option {
      min-width: 0;
      height: auto;
      padding: 12px 4px;
      line-height: 1.15;
      white-space: normal;
""",
    'unit add option vertical padding',
)

checks = [
    '<title>WH40k 11th V31.12</title>',
    'const APP_VERSION = "31.12";',
    "version: 'V31.12',",
    'padding: 12px 4px;',
    'CHANGE NOTE - WH40k_11th_V31.12'
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))

path.write_text(text, encoding="utf-8")
print("Patched WH40k_11th.html to V31.12")
