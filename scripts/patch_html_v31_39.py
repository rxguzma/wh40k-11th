from pathlib import Path
import re

source = Path("versions/WH40k_11th_V31.38.html")
path = Path("WH40k_11th.html")
text = source.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    text = text.replace(old, new, 1)


replace_once('<title>WH40k 11th V31.38</title>', '<title>WH40k 11th V31.39</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.38;', 'The current baseline is WH40k_11th_V31.39;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.38";', 'const APP_VERSION = "31.39";', 'APP_VERSION')
replace_once("version: 'V31.38',", "version: 'V31.39',", 'InternalQuality version')

# Remove the View header's Unit label so the four filters can use the entire
# first roster column. Do not change row height, filter behavior, or stat columns.
replace_once('<span class="view-roster-head-unit-label">Unit</span>', '', 'remove Unit header label')

layout_css = '''
    /* V31.39: filters own the full first View-header column. */
    .view-roster-head .roster-view-head-title {
      gap: 0 !important;
    }

    .view-roster-weapon-filter-actions {
      width: 100% !important;
      flex: 1 1 100% !important;
    }
'''
style_close = text.rfind('</style>')
if style_close < 0:
    raise SystemExit('closing style tag not found')
text = text[:style_close] + layout_css + text[style_close:]

old_invariant = 'Unit-level Tags remain on the Unit-level tag line.\n'
new_invariant = 'Unit-level Tags remain on the Unit-level tag line. The View roster header has no Unit text label; Range | Melee | Other | All fill the entire first roster column without changing the shared View/Edit header height.\n'
replace_once(old_invariant, new_invariant, 'View roster header invariant')

note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.38\n"
if note_marker not in text:
    raise SystemExit('release note insertion marker missing')
new_note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.39
    Scope: Remove the Unit label from the View roster header and let Range | Melee | Other | All use the full first-column width. Preserve the V31.38 equal-width 2.5px-gap layout, 24px control height, shared View/Edit header height, filter behavior, and all stat-column geometry.
    Risk areas: View roster header label/available filter width only.
  -->

'''
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.32\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f'old release note removal: expected 1 match, found {removed}')

checks = [
    '<title>WH40k 11th V31.39</title>',
    'const APP_VERSION = "31.39";',
    "version: 'V31.39',",
    'CHANGE NOTE - WH40k_11th_V31.39',
    'width: 100% !important;',
    'flex: 1 1 100% !important;',
    'Range | Melee | Other | All fill the entire first roster column',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))
if '<span class="view-roster-head-unit-label">Unit</span>' in text:
    raise SystemExit('Unit header label still present')

path.write_text(text, encoding='utf-8')
print('Built WH40k_11th.html as V31.39 with full-width roster filter group and no Unit label')
