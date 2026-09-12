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
replace_once('<title>WH40k 11th V31.9</title>', '<title>WH40k 11th V31.10</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.9;', 'The current baseline is WH40k_11th_V31.10;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.9";', 'const APP_VERSION = "31.10";', 'APP_VERSION')
replace_once("version: 'V31.9',", "version: 'V31.10',", 'InternalQuality version')

note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.9\n"
if note_marker not in text:
    raise SystemExit("release note insertion marker missing")
new_note = """  <!--
    CHANGE NOTE - WH40k_11th_V31.10
    Scope: Detachment Rule keyword eligibility editing is now presented as three clearly separate edit sections: Required, Any, and Excluded. Data fields and save behavior are unchanged.
    Risk areas: Detachment Rule keyword editor presentation only. Eligibility logic, CSV mapping, Enhancements, Stratagems, and unrelated roster UI are unchanged.
  -->

"""
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.5\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f"old release note removal: expected 1 match, found {removed}")

# Make Required / Any / Excluded visibly separate edit sections instead of one combined block.
replace_once(
    """    .eligibility-keyword-editor-row {
      display: grid;
      grid-template-columns: minmax(104px, auto) minmax(0, 1fr);
      gap: var(--shell-control-gap);
      align-items: center;
      min-width: 0;
    }

    .eligibility-keyword-editor-label {
      color: var(--text-secondary);
      font-size: var(--font-meta);
      font-weight: 400;
      white-space: nowrap;
    }
""",
    """    .eligibility-keyword-editor-row {
      display: grid;
      grid-template-columns: 1fr;
      gap: 6px;
      min-width: 0;
      padding: 10px 12px;
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 8px;
    }

    .eligibility-keyword-editor-label {
      color: var(--text-secondary);
      font-size: var(--font-meta);
      font-weight: 600;
      white-space: nowrap;
    }
""",
    "eligibility keyword section styling",
)

replace_once(
    """      const fields = [
        ["requiredKeywords", "Required Keywords", "Required_Keywords"],
        ["anyKeywords", "Any Keywords", "Any_Keywords"],
        ["excludedKeywords", "Excluded Keywords", "Excluded_Keywords"]
      ];
""",
    """      const fields = [
        ["requiredKeywords", "Required", "Required_Keywords"],
        ["anyKeywords", "Any", "Any_Keywords"],
        ["excludedKeywords", "Excluded", "Excluded_Keywords"]
      ];
""",
    "eligibility keyword section labels",
)

checks = [
    '<title>WH40k 11th V31.10</title>',
    'const APP_VERSION = "31.10";',
    "version: 'V31.10',",
    '["requiredKeywords", "Required", "Required_Keywords"]',
    '["anyKeywords", "Any", "Any_Keywords"]',
    '["excludedKeywords", "Excluded", "Excluded_Keywords"]',
    'border: 1px solid rgba(255, 255, 255, 0.12);'
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))

path.write_text(text, encoding="utf-8")
print("Patched WH40k_11th.html to V31.10")
