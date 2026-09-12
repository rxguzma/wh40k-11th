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
replace_once('<title>WH40k 11th V31.12</title>', '<title>WH40k 11th V31.13</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.12;', 'The current baseline is WH40k_11th_V31.13;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.12";', 'const APP_VERSION = "31.13";', 'APP_VERSION')
replace_once("version: 'V31.12',", "version: 'V31.13',", 'InternalQuality version')

note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.12\n"
if note_marker not in text:
    raise SystemExit("release note insertion marker missing")
new_note = """  <!--
    CHANGE NOTE - WH40k_11th_V31.13
    Scope: Fix Unit + panel option sizing so three-line Enhancement/Stratagem labels fit inside their buttons. The add-option rule now outranks the generic category-button fixed height and uses a 56px minimum height with automatic row growth.
    Risk areas: Unit + panel option-button geometry only. Eligibility, selection behavior, and unrelated roster layout are unchanged.
  -->

"""
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.8\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f"old release note removal: expected 1 match, found {removed}")

# The generic .category-button rule later in the stylesheet owns a fixed 38px height.
# Use a more specific component selector so Unit + options can actually grow for wrapped labels.
replace_once(
    """    .view-edit-unit-add-option {
      min-width: 0;
      height: auto;
      padding: 12px 4px;
      line-height: 1.15;
      white-space: normal;
      overflow-wrap: anywhere;

      font-size: 10px;
      font-weight: 400;
    }
""",
    """    .category-button.view-edit-unit-add-option {
      min-width: 0;
      min-height: 56px;
      height: auto;
      padding: 6px 4px;
      line-height: 1.15;
      white-space: normal;
      overflow-wrap: anywhere;

      font-size: 10px;
      font-weight: 400;
    }
""",
    'unit add option fixed-height override',
)

checks = [
    '<title>WH40k 11th V31.13</title>',
    'const APP_VERSION = "31.13";',
    "version: 'V31.13',",
    '.category-button.view-edit-unit-add-option {',
    'min-height: 56px;',
    'CHANGE NOTE - WH40k_11th_V31.13'
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))

path.write_text(text, encoding="utf-8")
print("Patched WH40k_11th.html to V31.13")
