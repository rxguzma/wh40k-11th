from pathlib import Path
import re

source = Path("versions/WH40k_11th_V31.17.html")
path = Path("WH40k_11th.html")
text = source.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    text = text.replace(old, new, 1)


# Build strictly from V31.17 so its Waha handoff fix is preserved.
replace_once('<title>WH40k 11th V31.17</title>', '<title>WH40k 11th V31.18</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.17;', 'The current baseline is WH40k_11th_V31.18;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.17";', 'const APP_VERSION = "31.18";', 'APP_VERSION')
replace_once("version: 'V31.17',", "version: 'V31.18',", 'InternalQuality version')

# Remove only the green outline from the Unit + Enhancement/Stratagem panel.
pattern = re.compile(r'(<div class="subsection )active-unit-detail-box(" id="add-\$\{index\}">)')
text, changed = pattern.subn(r'\1\2', text, count=1)
if changed != 1:
    raise SystemExit(f"Unit + panel green outline: expected 1 match, found {changed}")

# Add the new detailed release note and keep only the five newest detailed notes.
note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.17\n"
if note_marker not in text:
    raise SystemExit("release note insertion marker missing")
new_note = """  <!--
    CHANGE NOTE - WH40k_11th_V31.18
    Scope: Build from V31.17 and remove the green outline from the Unit + Enhancement/Stratagem panel only.
    Risk areas: Unit + panel border styling only. V31.17 behavior, including Waha Chrome handoff, remains unchanged.
  -->

"""
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.13\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f"old release note removal: expected 1 match, found {removed}")

checks = [
    '<title>WH40k 11th V31.18</title>',
    'const APP_VERSION = "31.18";',
    "version: 'V31.18',",
    'CHANGE NOTE - WH40k_11th_V31.18',
    'CHANGE NOTE - WH40k_11th_V31.17'
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))

path.write_text(text, encoding="utf-8")
print("Built WH40k_11th.html as V31.18 from V31.17 with Unit + panel green outline removed")
