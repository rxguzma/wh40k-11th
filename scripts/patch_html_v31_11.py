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
replace_once('<title>WH40k 11th V31.10</title>', '<title>WH40k 11th V31.11</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.10;', 'The current baseline is WH40k_11th_V31.11;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.10";', 'const APP_VERSION = "31.11";', 'APP_VERSION')
replace_once("version: 'V31.10',", "version: 'V31.11',", 'InternalQuality version')

# Keep the version-distribution invariant explicit so the compact history layout does not regress.
replace_once(
    'The Version/current label toggles history without an arrow. The host runs releases in a fresh same-origin iframe,',
    'The Version/current label toggles history without an arrow. Version history renders as two rows of five version buttons for the ten retained releases, never as a one-version-per-row list. The host runs releases in a fresh same-origin iframe,',
    'version distribution invariant',
)

note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.10\n"
if note_marker not in text:
    raise SystemExit("release note insertion marker missing")
new_note = """  <!--
    CHANGE NOTE - WH40k_11th_V31.11
    Scope: Version history is now a compact ten-button grid: five version buttons per row across two rows instead of a long one-version-per-row list.
    Risk areas: Version history presentation only. Version loading, Update, Download, retention, and release-index behavior are unchanged.
  -->

"""
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.6\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f"old release note removal: expected 1 match, found {removed}")

# Compact the retained ten versions into exactly five columns. With the existing
# ten-version retention limit this produces two rows of five buttons.
replace_once(
    """    .version-history-list {
      display: grid;
      gap: var(--shell-control-gap);
    }

    .version-history-row {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: var(--shell-control-gap);
      align-items: center;
    }
""",
    """    .version-history-list {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: var(--shell-control-gap);
    }

    .version-history-row {
      display: block;
      min-width: 0;
    }
""",
    'version history grid',
)

replace_once(
    """    .version-history-select {
      width: 100%;
      min-width: 0;
      min-height: var(--view-edit-control-height);
      justify-content: flex-start;
      padding: 0 var(--btn-padding-x-md);
      font-size: var(--font-meta);
    }
""",
    """    .version-history-select {
      width: 100%;
      min-width: 0;
      min-height: var(--view-edit-control-height);
      justify-content: center;
      padding: 0 2px;
      font-size: var(--font-meta);
      white-space: nowrap;
    }
""",
    'version history button alignment',
)

replace_once(
    """    .version-history-meta {
      color: var(--text-muted);
      font-size: var(--font-badge);
      font-weight: 700;
      line-height: 1;
      white-space: nowrap;
""",
    """    .version-history-meta {
      display: none;
      color: var(--text-muted);
      font-size: var(--font-badge);
      font-weight: 700;
      line-height: 1;
      white-space: nowrap;
""",
    'version history metadata visibility',
)

checks = [
    '<title>WH40k 11th V31.11</title>',
    'const APP_VERSION = "31.11";',
    "version: 'V31.11',",
    'grid-template-columns: repeat(5, minmax(0, 1fr));',
    '.version-history-row {\n      display: block;',
    '.version-history-meta {\n      display: none;',
    'two rows of five version buttons'
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))

path.write_text(text, encoding="utf-8")
print("Patched WH40k_11th.html to V31.11")
