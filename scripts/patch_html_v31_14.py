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
replace_once('<title>WH40k 11th V31.13</title>', '<title>WH40k 11th V31.14</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.13;', 'The current baseline is WH40k_11th_V31.14;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.13";', 'const APP_VERSION = "31.14";', 'APP_VERSION')
replace_once("version: 'V31.13',", "version: 'V31.14',", 'InternalQuality version')

note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.13\n"
if note_marker not in text:
    raise SystemExit("release note insertion marker missing")
new_note = """  <!--
    CHANGE NOTE - WH40k_11th_V31.14
    Scope: Increase the actual Unit + Enhancement/Stratagem option-button height so three-line labels sit fully inside their boxes. Minimum height is now 68px with 8px vertical padding.
    Risk areas: Unit + panel option-button geometry only. Eligibility, selection behavior, and unrelated roster layout are unchanged.
  -->

"""
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.9\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f"old release note removal: expected 1 match, found {removed}")

replace_once(
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
    """    .category-button.view-edit-unit-add-option {
      min-width: 0;
      min-height: 68px;
      height: auto;
      padding: 8px 4px;
      line-height: 1.15;
      white-space: normal;
      overflow-wrap: anywhere;

      font-size: 10px;
      font-weight: 400;
    }
""",
    'unit add option height',
)

checks = [
    '<title>WH40k 11th V31.14</title>',
    'const APP_VERSION = "31.14";',
    "version: 'V31.14',",
    '.category-button.view-edit-unit-add-option {',
    'min-height: 68px;',
    'padding: 8px 4px;',
    'CHANGE NOTE - WH40k_11th_V31.14'
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))

path.write_text(text, encoding="utf-8")
print("Patched WH40k_11th.html to V31.14")
