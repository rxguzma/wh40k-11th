from pathlib import Path
import re

source = Path("versions/WH40k_11th_V31.35.html")
path = Path("WH40k_11th.html")
text = source.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    text = text.replace(old, new, 1)


# Sequential release metadata.
replace_once('<title>WH40k 11th V31.35</title>', '<title>WH40k 11th V31.36</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.35;', 'The current baseline is WH40k_11th_V31.36;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.35";', 'const APP_VERSION = "31.36";', 'APP_VERSION')
replace_once("version: 'V31.35',", "version: 'V31.36',", 'InternalQuality version')

# V31.36: equalize the four View roster filter widths and cut the visible
# spacing between adjacent buttons to roughly half of V31.34/V31.35.
filter_css = '''
    /* V31.36: equal-width, tighter View roster filter buttons. */
    .view-roster-weapon-filter-button {
      flex: 0 0 60px !important;
      width: 60px !important;
      min-width: 60px !important;
      max-width: 60px !important;
      box-sizing: border-box !important;
      padding-left: 0 !important;
      padding-right: 0 !important;
      margin-left: -2px !important;
      margin-right: -2px !important;
      justify-self: start !important;
      white-space: nowrap !important;
    }
'''
style_close = text.rfind('</style>')
if style_close < 0:
    raise SystemExit('closing style tag not found')
text = text[:style_close] + filter_css + text[style_close:]

# Add the new detailed release note and keep only the five newest detailed notes.
note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.35\n"
if note_marker not in text:
    raise SystemExit('release note insertion marker missing')
new_note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.36
    Scope: Make Range | Melee | Other | All exactly the same 60px width and reduce the visible separation between adjacent buttons to roughly half of the prior spacing. Height, labels, colors, and filtering behavior are unchanged.
    Risk areas: View roster filter-button sizing and spacing only.
  -->

'''
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.31\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f'old release note removal: expected 1 match, found {removed}')

checks = [
    '<title>WH40k 11th V31.36</title>',
    'const APP_VERSION = "31.36";',
    "version: 'V31.36',",
    'CHANGE NOTE - WH40k_11th_V31.36',
    'flex: 0 0 60px !important;',
    'width: 60px !important;',
    'min-width: 60px !important;',
    'max-width: 60px !important;',
    'margin-left: -2px !important;',
    'margin-right: -2px !important;',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))

path.write_text(text, encoding='utf-8')
print('Built WH40k_11th.html as V31.36 with equal-width tighter roster filter buttons')
