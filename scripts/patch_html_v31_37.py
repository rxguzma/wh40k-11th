from pathlib import Path
import re

source = Path("versions/WH40k_11th_V31.36.html")
path = Path("WH40k_11th.html")
text = source.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    text = text.replace(old, new, 1)


replace_once('<title>WH40k 11th V31.36</title>', '<title>WH40k 11th V31.37</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.36;', 'The current baseline is WH40k_11th_V31.37;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.36";', 'const APP_VERSION = "31.37";', 'APP_VERSION')
replace_once("version: 'V31.36',", "version: 'V31.37',", 'InternalQuality version')

# V31.37: keep all four controls equal width, but make the group fit entirely
# inside the Unit header on phone layouts. 48px is wide enough for the longest
# label while removing the overflow into the M\" column. Keep only a 2px total
# visual gap between adjacent controls.
fit_css = '''
    /* V31.37: equal-width roster filters fitted inside the Unit header. */
    .view-roster-weapon-filter-button {
      box-sizing: border-box !important;
      width: 48px !important;
      min-width: 48px !important;
      max-width: 48px !important;
      flex: 0 0 48px !important;
      padding-left: 2px !important;
      padding-right: 2px !important;
      margin-left: 1px !important;
      margin-right: 1px !important;
      white-space: nowrap !important;
    }
'''
style_close = text.rfind('</style>')
if style_close < 0:
    raise SystemExit('closing style tag not found')
text = text[:style_close] + fit_css + text[style_close:]

note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.36\n"
if note_marker not in text:
    raise SystemExit('release note insertion marker missing')
new_note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.37
    Scope: Keep Range | Melee | Other | All equal width while reducing each button to 48px so the complete filter group stays inside the Unit header on phone layouts. Adjacent-button spacing is 2px total. Height, labels, colors, and filter behavior are unchanged.
    Risk areas: View roster filter-button width and horizontal spacing only.
  -->

'''
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.32\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f'old release note removal: expected 1 match, found {removed}')

checks = [
    '<title>WH40k 11th V31.37</title>',
    'const APP_VERSION = "31.37";',
    "version: 'V31.37',",
    'CHANGE NOTE - WH40k_11th_V31.37',
    'width: 48px !important;',
    'min-width: 48px !important;',
    'max-width: 48px !important;',
    'flex: 0 0 48px !important;',
    'margin-left: 1px !important;',
    'margin-right: 1px !important;',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))

path.write_text(text, encoding='utf-8')
print('Built WH40k_11th.html as V31.37 with equal-width roster filters fitted inside Unit header')
