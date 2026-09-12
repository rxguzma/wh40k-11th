from pathlib import Path
import re

source = Path("versions/WH40k_11th_V31.32.html")
path = Path("WH40k_11th.html")
text = source.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    text = text.replace(old, new, 1)


# Sequential release metadata.
replace_once('<title>WH40k 11th V31.32</title>', '<title>WH40k 11th V31.33</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.32;', 'The current baseline is WH40k_11th_V31.33;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.32";', 'const APP_VERSION = "31.33";', 'APP_VERSION')
replace_once("version: 'V31.32',", "version: 'V31.33',", 'InternalQuality version')

# Keep the four View roster filters compact. Their height and behavior are
# unchanged; only horizontal stretching is removed so each button sizes to text.
compact_css = '''
    /* V31.33: compact View roster Range / Melee / Other / All buttons. */
    .view-roster-weapon-filter-button {
      flex: 0 0 auto !important;
      width: auto !important;
      min-width: 0 !important;
      padding-left: 10px !important;
      padding-right: 10px !important;
    }
'''
style_close = text.rfind('</style>')
if style_close < 0:
    raise SystemExit('closing style tag not found')
text = text[:style_close] + compact_css + text[style_close:]

# Add the new release note and retain the five newest detailed notes.
note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.32\n"
if note_marker not in text:
    raise SystemExit('release note insertion marker missing')
new_note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.33
    Scope: Make the View roster Range | Melee | Other | All filter buttons compact instead of horizontally stretched. Button height, labels, colors, single-select behavior, and filtering logic are unchanged.
    Risk areas: View roster filter-button sizing only.
  -->

'''
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.28\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f'old release note removal: expected 1 match, found {removed}')

checks = [
    '<title>WH40k 11th V31.33</title>',
    'const APP_VERSION = "31.33";',
    "version: 'V31.33',",
    'CHANGE NOTE - WH40k_11th_V31.33',
    '.view-roster-weapon-filter-button {',
    'flex: 0 0 auto !important;',
    'width: auto !important;',
    'min-width: 0 !important;',
    'padding-left: 10px !important;',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))

path.write_text(text, encoding='utf-8')
print('Built WH40k_11th.html as V31.33 with compact roster filter buttons')
