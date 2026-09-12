from pathlib import Path
import re

source = Path("versions/WH40k_11th_V31.39.html")
path = Path("WH40k_11th.html")
text = source.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    text = text.replace(old, new, 1)


replace_once('<title>WH40k 11th V31.39</title>', '<title>WH40k 11th V31.40</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.39;', 'The current baseline is WH40k_11th_V31.40;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.39";', 'const APP_VERSION = "31.40";', 'APP_VERSION')
replace_once("version: 'V31.39',", "version: 'V31.40',", 'InternalQuality version')

old_actions = '''    <div class="title-right-actions">
      <button id="viewModeToggle" class="secondary app-mode-button" aria-pressed="true" onclick="event.stopPropagation(); UI.selectAppMode('view')">View</button>
      <button id="editModeToggle" class="secondary app-mode-button edit-mode-toggle" aria-pressed="false" onclick="event.stopPropagation(); UI.selectAppMode('edit')">Edit</button>
      <button id="cardsModeToggle" class="secondary app-mode-button" aria-pressed="false" onclick="event.stopPropagation(); UI.selectAppMode('cards')">Cards</button>
      <span id="appTitlePoints" class="title-points"></span>
    </div>'''
new_actions = '''    <div class="title-right-actions">
      <div class="app-mode-button-grid">
        <button id="viewModeToggle" class="secondary app-mode-button" aria-pressed="true" onclick="event.stopPropagation(); UI.selectAppMode('view')">View</button>
        <button id="editModeToggle" class="secondary app-mode-button edit-mode-toggle" aria-pressed="false" onclick="event.stopPropagation(); UI.selectAppMode('edit')">Edit</button>
        <button id="cardsModeToggle" class="secondary app-mode-button" aria-pressed="false" onclick="event.stopPropagation(); UI.selectAppMode('cards')">Cards</button>
        <button id="newPageModeToggle" class="secondary app-mode-button new-page-mode-toggle" aria-pressed="false" onclick="event.stopPropagation(); UI.selectAppMode('newpage')">New Page</button>
      </div>
      <span id="appTitlePoints" class="title-points"></span>
    </div>'''
replace_once(old_actions, new_actions, 'title mode controls')

letters = "ABCDEFGH"
column_labels = "\n".join(
    f'      <div class="new-page-grid-col-label" style="grid-column:{index + 2};grid-row:1">{letter}</div>'
    for index, letter in enumerate(letters)
)
grid_rows = []
for row in range(1, 21):
    grid_rows.append(f'      <div class="new-page-grid-row-label" style="grid-column:1;grid-row:{row + 1}">{row}</div>')
    for col in range(8):
        grid_rows.append(f'      <div class="new-page-grid-cell" style="grid-column:{col + 2};grid-row:{row + 1}"></div>')
cells = "\n".join(grid_rows)

new_page_screen = f'''  <div id="newPageScreen" class="screen new-page-screen" aria-label="New page">
    <div class="new-page-draft-grid" aria-label="Layout grid">
{column_labels}
{cells}
      <div class="new-page-grid-title">Army Builder</div>
    </div>
  </div>

'''
replace_once('  <div id="rosterScreen" class="screen active">\n', new_page_screen + '  <div id="rosterScreen" class="screen active">\n', 'new page screen')

layout_css = '''
    /* V31.40: phone-first drafting grid for the approved New Page surface. */
    :root {
      --new-page-grid-label-width: 26px;
      --new-page-grid-label-height: 24px;
      --new-page-grid-cell: calc((100vw - var(--new-page-grid-label-width)) / 8);
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
      grid-template-columns: var(--new-page-grid-label-width) repeat(8, var(--new-page-grid-cell));
      grid-template-rows: var(--new-page-grid-label-height) repeat(20, var(--new-page-grid-cell));
      width: 100vw;
      background: var(--color-bg-page);
      color: var(--text-body);
    }

    .new-page-grid-col-label,
    .new-page-grid-row-label {
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--text-muted);
      font-size: var(--font-meta);
      font-weight: 700;
      line-height: 1;
      user-select: none;
    }

    .new-page-grid-col-label,
    .new-page-grid-row-label,
    .new-page-grid-cell {
      border-right: 1px solid var(--color-border-default);
      border-bottom: 1px solid var(--color-border-default);
    }

    .new-page-grid-cell {
      min-width: 0;
      min-height: 0;
    }

    .new-page-grid-title {
      grid-column: 2 / span 8;
      grid-row: 2;
      z-index: 2;
      display: flex;
      align-items: center;
      padding: 0 var(--shell-control-gap);
      color: var(--text-primary);
      font-size: var(--font-title);
      font-weight: 900;
      line-height: 1;
      pointer-events: none;
    }

    @media (max-width: 430px) {
      .app-mode-button-grid {
        grid-template-columns: repeat(3, var(--btn-width-mini-mobile));
      }
    }
'''
style_close = text.rfind('</style>')
if style_close < 0:
    raise SystemExit('closing style tag not found')
text = text[:style_close] + layout_css + text[style_close:]

old_select_start = '''    function selectAppMode(mode) {
      const target = String(mode || "").trim().toLowerCase();

      if (target === "cards") {'''
new_select_start = '''    function selectAppMode(mode) {
      const target = String(mode || "").trim().toLowerCase();

      if (target === "newpage") {
        showNewPageScreen();
        return;
      }

      if (activeAppScreen === "newpage") hideNewPageScreen();

      if (target === "cards") {'''
replace_once(old_select_start, new_select_start, 'selectAppMode new page routing')

new_page_functions = '''
    function showNewPageScreen() {
      if (activeAppScreen === "cards") showArmyScreen({ commitCardsState: true });
      closeTitleRosterMenu();

      const rosterScreen = document.getElementById("rosterScreen");
      const cardsScreen = document.getElementById("cardsScreen");
      const newPageScreen = document.getElementById("newPageScreen");
      if (!newPageScreen) return;

      if (rosterScreen) rosterScreen.classList.remove("active");
      if (cardsScreen) cardsScreen.classList.remove("active");
      newPageScreen.classList.add("active");
      activeAppScreen = "newpage";

      const newPageButton = document.getElementById("newPageModeToggle");
      const viewButton = document.getElementById("viewModeToggle");
      const editButton = document.getElementById("editModeToggle");
      const cardsButton = document.getElementById("cardsModeToggle");
      [viewButton, editButton, cardsButton].forEach(button => {
        if (!button) return;
        button.classList.remove("active");
        button.setAttribute("aria-pressed", "false");
      });
      if (newPageButton) {
        newPageButton.classList.add("active");
        newPageButton.setAttribute("aria-pressed", "true");
      }
      window.scrollTo({ top: 0, left: 0, behavior: "auto" });
    }

    function hideNewPageScreen() {
      const rosterScreen = document.getElementById("rosterScreen");
      const newPageScreen = document.getElementById("newPageScreen");
      const newPageButton = document.getElementById("newPageModeToggle");

      if (newPageScreen) newPageScreen.classList.remove("active");
      if (rosterScreen) rosterScreen.classList.add("active");
      activeAppScreen = "army";

      if (newPageButton) {
        newPageButton.classList.remove("active");
        newPageButton.setAttribute("aria-pressed", "false");
      }
      updateEditModeToggle();
    }

'''
marker = '    // UI ownership: direct title navigation replaces the retired cycling-only\n'
if text.count(marker) != 1:
    raise SystemExit(f'new page function insertion marker: expected 1 match, found {text.count(marker)}')
text = text.replace(marker, new_page_functions + marker, 1)

note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.39\n"
if note_marker not in text:
    raise SystemExit('release note insertion marker missing')
new_note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.40
    Scope: Add the approved New Page control beneath View/Edit and a phone-first drafting-grid screen. The grid fills the phone width with eight equal columns, visible A-H column labels and numbered rows, and begins with only the Army Builder title. Existing app typography, semantic colors, and button styling are reused.
    Risk areas: title control layout and new-page navigation only. Existing View, Edit, Cards, roster data, and combat behavior are unchanged.
  -->

'''
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.33\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f'old release note removal: expected 1 match, found {removed}')

checks = [
    '<title>WH40k 11th V31.40</title>',
    'const APP_VERSION = "31.40";',
    "version: 'V31.40',",
    'CHANGE NOTE - WH40k_11th_V31.40',
    'id="newPageModeToggle"',
    '>New Page</button>',
    'id="newPageScreen"',
    'class="new-page-grid-title">Army Builder</div>',
    '--new-page-grid-cell: calc((100vw - var(--new-page-grid-label-width)) / 8);',
    'function showNewPageScreen()',
    'function hideNewPageScreen()',
    'if (target === "newpage")',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))

path.write_text(text, encoding='utf-8')
print('Built WH40k_11th.html as V31.40 with phone-first New Page drafting grid')
