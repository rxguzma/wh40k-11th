from pathlib import Path
import re

source = Path("versions/WH40k_11th_V31.33.html")
path = Path("WH40k_11th.html")
text = source.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    text = text.replace(old, new, 1)


replace_once('<title>WH40k 11th V31.33</title>', '<title>WH40k 11th V31.34</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.33;', 'The current baseline is WH40k_11th_V31.34;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.33";', 'const APP_VERSION = "31.34";', 'APP_VERSION')
replace_once("version: 'V31.33',", "version: 'V31.34',", 'InternalQuality version')

# V31.34: make the four roster filters genuinely compact. V31.33 removed flex
# growth but left enough intrinsic width/padding that the row could still spill
# into the M" column on phone layouts. These rules force content-sized controls
# in either flex or grid parents and reduce only horizontal footprint.
compact_css = '''
    /* V31.34: truly compact View roster Range / Melee / Other / All buttons. */
    .view-roster-weapon-filter-button {
      flex: 0 0 auto !important;
      width: max-content !important;
      min-width: 0 !important;
      max-width: max-content !important;
      justify-self: start !important;
      padding-left: 4px !important;
      padding-right: 4px !important;
      margin-left: 1px !important;
      margin-right: 1px !important;
      white-space: nowrap !important;
    }
'''
style_close = text.rfind('</style>')
if style_close < 0:
    raise SystemExit('closing style tag not found')
text = text[:style_close] + compact_css + text[style_close:]

note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.33\n"
if note_marker not in text:
    raise SystemExit('release note insertion marker missing')
new_note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.34
    Scope: Reduce the horizontal footprint of Range | Melee | Other | All so the four controls remain inside the Unit header on phone layouts. Buttons are content-sized, cannot flex/grid-stretch, and use 4px horizontal padding. Height, filtering behavior, colors, and labels are unchanged.
    Risk areas: View roster filter-button sizing only.
  -->

'''
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.29\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f'old release note removal: expected 1 match, found {removed}')

checks = [
    '<title>WH40k 11th V31.34</title>',
    'const APP_VERSION = "31.34";',
    "version: 'V31.34',",
    'CHANGE NOTE - WH40k_11th_V31.34',
    'width: max-content !important;',
    'max-width: max-content !important;',
    'justify-self: start !important;',
    'padding-left: 4px !important;',
    'padding-right: 4px !important;',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))

path.write_text(text, encoding='utf-8')
print('Built WH40k_11th.html as V31.34 with genuinely compact roster filter buttons')
