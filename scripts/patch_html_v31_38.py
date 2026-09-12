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


replace_once('<title>WH40k 11th V31.35</title>', '<title>WH40k 11th V31.38</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.35;', 'The current baseline is WH40k_11th_V31.38;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.35";', 'const APP_VERSION = "31.38";', 'APP_VERSION')
replace_once("version: 'V31.35',", "version: 'V31.38',", 'InternalQuality version')

# Start from the V31.35 visual baseline. Make the four filters share the
# available Unit-header width equally instead of hard-coding a pixel width.
# Their height stays exactly on the Edit header's 24px control contract, and
# the View header is explicitly locked to the same row-height formula as Edit.
layout_css = '''
    /* V31.38: responsive equal-width roster filters; View height matches Edit. */
    .view-roster-head {
      height: calc(var(--edit-header-button-height) + 20px) !important;
      min-height: calc(var(--edit-header-button-height) + 20px) !important;
      max-height: calc(var(--edit-header-button-height) + 20px) !important;
    }

    .view-roster-head .roster-view-head-title {
      display: flex !important;
      align-items: center !important;
      min-width: 0 !important;
      overflow: hidden !important;
    }

    .view-roster-weapon-filter-actions {
      display: grid !important;
      grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
      flex: 1 1 0 !important;
      min-width: 0 !important;
      gap: 2.5px !important;
      margin-left: 0 !important;
    }

    .view-roster-weapon-filter-button {
      box-sizing: border-box !important;
      width: 100% !important;
      min-width: 0 !important;
      max-width: none !important;
      height: var(--edit-header-button-height) !important;
      min-height: var(--edit-header-button-height) !important;
      max-height: var(--edit-header-button-height) !important;
      padding-left: 2px !important;
      padding-right: 2px !important;
      margin: 0 !important;
      white-space: nowrap !important;
    }

    @media (max-width: 430px) {
      .view-roster-head {
        height: calc(var(--edit-header-button-height) + 18px) !important;
        min-height: calc(var(--edit-header-button-height) + 18px) !important;
        max-height: calc(var(--edit-header-button-height) + 18px) !important;
      }
    }
'''
style_close = text.rfind('</style>')
if style_close < 0:
    raise SystemExit('closing style tag not found')
text = text[:style_close] + layout_css + text[style_close:]

note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.35\n"
if note_marker not in text:
    raise SystemExit('release note insertion marker missing')
new_note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.38
    Scope: Return to the V31.35 roster-filter visual baseline, then make Range | Melee | Other | All equal-width by sharing the remaining Unit-header space responsively. Adjacent spacing is 2.5px, exactly half the existing 5px shell-control gap. Filter controls remain 24px high and the View header is locked to the same row-height formula as Edit on desktop and phone layouts.
    Risk areas: View roster filter layout and View header geometry only. Filter behavior, colors, labels, roster data, and Edit mode are unchanged.
  -->

'''
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.31\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f'old release note removal: expected 1 match, found {removed}')

checks = [
    '<title>WH40k 11th V31.38</title>',
    'const APP_VERSION = "31.38";',
    "version: 'V31.38',",
    'CHANGE NOTE - WH40k_11th_V31.38',
    'grid-template-columns: repeat(4, minmax(0, 1fr)) !important;',
    'gap: 2.5px !important;',
    'height: var(--edit-header-button-height) !important;',
    'height: calc(var(--edit-header-button-height) + 18px) !important;',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))

path.write_text(text, encoding='utf-8')
print('Built WH40k_11th.html as V31.38 with responsive equal-width roster filters and Edit-matched header height')