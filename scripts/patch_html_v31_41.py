from pathlib import Path
import re

source = Path("versions/WH40k_11th_V31.40.html")
path = Path("WH40k_11th.html")
text = source.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    text = text.replace(old, new, 1)


replace_once('<title>WH40k 11th V31.40</title>', '<title>WH40k 11th V31.41</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.40;', 'The current baseline is WH40k_11th_V31.41;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.40";', 'const APP_VERSION = "31.41";', 'APP_VERSION')
replace_once("version: 'V31.40',", "version: 'V31.41',", 'InternalQuality version')

letters = "ABCDEFGH"
items = []
for row in range(1, 21):
    for col, letter in enumerate(letters, start=1):
        labels = []
        if row == 1:
            labels.append(f'<span class="new-page-grid-col-coordinate">{letter}</span>')
        if col == 1:
            labels.append(f'<span class="new-page-grid-row-coordinate">{row}</span>')
        label_html = ''.join(labels)
        items.append(
            f'      <div class="new-page-grid-cell" style="grid-column:{col};grid-row:{row}">{label_html}</div>'
        )
cell_html = "\n".join(items)
new_screen = f'''  <div id="newPageScreen" class="screen new-page-screen" aria-label="New page">
    <div class="new-page-draft-grid" aria-label="Layout grid">
{cell_html}
      <div class="new-page-grid-title">Army Builder</div>
    </div>
  </div>

  <div id="rosterScreen" class="screen active">'''

pattern = re.compile(
    r'  <div id="newPageScreen" class="screen new-page-screen" aria-label="New page">.*?\n\n  <div id="rosterScreen" class="screen active">',
    re.S,
)
text, count = pattern.subn(new_screen, text, count=1)
if count != 1:
    raise SystemExit(f'new page screen replacement: expected 1 match, found {count}')

new_css = '''
    /* V31.41: fixed phone grid uses the same 52px mobile action size as the existing roster controls. */
    :root {
      --new-page-grid-cell: var(--btn-width-action-mobile);
    }

    .app-mode-button-grid {
      display: grid;
      grid-template-columns: repeat(3, var(--btn-width-mini));
      gap: var(--view-edit-multi-select-gap);
      align-items: center;
    }

    .new-page-mode-toggle {
      grid-column: 1 / span 2;
      width: 100% !important;
      min-width: 0 !important;
      max-width: none !important;
    }

    .new-page-screen {
      width: 100vw;
      margin-left: calc(50% - 50vw);
      overflow-x: hidden;
      background: var(--color-bg-page);
    }

    .new-page-draft-grid {
      display: grid;
      grid-template-columns: repeat(8, var(--new-page-grid-cell));
      grid-auto-rows: var(--new-page-grid-cell);
      width: max-content;
      margin: 0 auto;
      border-top: 1px solid var(--color-border-default);
      border-left: 1px solid var(--color-border-default);
      background: var(--color-bg-page);
      color: var(--text-body);
    }

    .new-page-grid-cell {
      position: relative;
      width: var(--new-page-grid-cell);
      height: var(--new-page-grid-cell);
      min-width: var(--new-page-grid-cell);
      min-height: var(--new-page-grid-cell);
      border-right: 1px solid var(--color-border-default);
      border-bottom: 1px solid var(--color-border-default);
    }

    .new-page-grid-col-coordinate,
    .new-page-grid-row-coordinate {
      position: absolute;
      color: var(--text-muted);
      font-size: var(--font-meta);
      font-weight: 700;
      line-height: 1;
      user-select: none;
      pointer-events: none;
    }

    .new-page-grid-col-coordinate {
      top: 4px;
      left: 50%;
      transform: translateX(-50%);
    }

    .new-page-grid-row-coordinate {
      left: 4px;
      bottom: 4px;
    }

    .new-page-grid-title {
      grid-column: 1 / span 8;
      grid-row: 2;
      z-index: 2;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0 var(--shell-control-gap);
      color: var(--text-primary);
      font-size: var(--font-title);
      font-weight: 900;
      line-height: 1;
      background: transparent;
      pointer-events: none;
    }

    @media (max-width: 430px) {
      .app-mode-button-grid {
        grid-template-columns: repeat(3, var(--btn-width-mini-mobile));
      }
    }
'''

css_pattern = re.compile(
    r'\n    /\* V31\.40: phone-first drafting grid for the approved New Page surface\. \*/.*?\n</style>',
    re.S,
)
text, count = css_pattern.subn(new_css + '</style>', text, count=1)
if count != 1:
    raise SystemExit(f'grid css replacement: expected 1 match, found {count}')

note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.40\n"
if note_marker not in text:
    raise SystemExit('release note insertion marker missing')
new_note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.41
    Scope: Correct New Page grid geometry. Every grid square now uses the existing 52px mobile action-control size instead of stretching to fill the viewport. Letter coordinates are embedded in the top-row squares and row numbers are embedded in the left-column squares; there is no separate label row or label column. Army Builder remains the only page content.
    Risk areas: New Page grid geometry only. Existing View, Edit, Cards, roster data, and combat behavior are unchanged.
  -->

'''
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.35\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f'old release note removal: expected 1 match, found {removed}')

checks = [
    '<title>WH40k 11th V31.41</title>',
    'const APP_VERSION = "31.41";',
    "version: 'V31.41',",
    'CHANGE NOTE - WH40k_11th_V31.41',
    '--new-page-grid-cell: var(--btn-width-action-mobile);',
    'grid-template-columns: repeat(8, var(--new-page-grid-cell));',
    'class="new-page-grid-col-coordinate">A</span>',
    'class="new-page-grid-row-coordinate">1</span>',
    'class="new-page-grid-title">Army Builder</div>',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))
if 'new-page-grid-col-label' in text or 'new-page-grid-row-label' in text:
    raise SystemExit('separate coordinate label row/column still present')

path.write_text(text, encoding='utf-8')
print('Built WH40k_11th.html as V31.41 with fixed 52px square phone grid and embedded coordinates')
