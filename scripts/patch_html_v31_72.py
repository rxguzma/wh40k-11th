from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.71.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


replace_once('<title>WH40k 11th V31.71</title>', '<title>WH40k 11th V31.72</title>', 'title')
replace_once('The current baseline is WH40k_11th_V31.71;', 'The current baseline is WH40k_11th_V31.72;', 'baseline')
replace_once('const APP_VERSION = "31.71";', 'const APP_VERSION = "31.72";', 'APP_VERSION')
replace_once("version: 'V31.71',", "version: 'V31.72',", 'quality version')

frame_pattern = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
match = frame_pattern.search(text)
if not match:
    raise SystemExit('alternate View iframe not found')
np = html.unescape(match.group(2))

# From the new View, EDIT goes through the parent router so the first press
# opens legacy Edit. On the new Edit surface, VIEW returns locally to new View.
old_nav = "b.onclick=()=>{if(t==='edit'||(p==='edit'&&t==='view'))renderPage(t);else parent.UI.selectAppMode(t)};"
new_nav = "b.onclick=()=>{if(p==='edit'&&t==='view')renderPage('view');else if(p==='edit'&&t==='edit')return;else parent.UI.selectAppMode(t)};"
if np.count(old_nav) != 1:
    raise SystemExit(f'alternate navigation handler: expected 1 match, found {np.count(old_nav)}')
np = np.replace(old_nav, new_nav, 1)

for required in [
    "if(p==='edit'&&t==='view')renderPage('view')",
    "else if(p==='edit'&&t==='edit')return",
    "else parent.UI.selectAppMode(t)",
    "function renderPage(p)",
]:
    if required not in np:
        raise SystemExit('alternate Edit routing check failed: ' + required)

np_srcdoc = html.escape(np, quote=True)
text = text[:match.start(2)] + np_srcdoc + text[match.end(2):]

# Edit mirrors View's two-press behavior. First press enters existing Edit.
# If Edit is already active, second press opens the alternate surface and calls
# its existing global renderPage('edit') function to show the blank new Edit.
edit_pattern = re.compile(
    r'''      if \(target === "edit"\) \{\n.*?\n      \}\n\n      if \(target === "view"\) \{''',
    re.S,
)
edit_match = edit_pattern.search(text)
if not edit_match:
    raise SystemExit('parent Edit routing branch not found')
new_edit_branch = '''      if (target === "edit") {
        if (activeAppScreen === "cards") showArmyScreen({ commitCardsState: true });
        if (appEditMode) {
          showNewPageScreen();
          const npFrame = document.getElementById("npViewFrame");
          try {
            const npWindow = npFrame && npFrame.contentWindow;
            if (npWindow && typeof npWindow.renderPage === "function") npWindow.renderPage("edit");
          } catch (_) {}
          return;
        }
        setEditMode(true);
        return;
      }

      if (target === "view") {'''
text = text[:edit_match.start()] + new_edit_branch + text[edit_match.end():]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.72
    Scope: Make Edit use the same two-press navigation pattern as View. From canonical View, the first Edit press opens the existing/legacy Edit exactly as before. Pressing Edit again while Edit is already active opens the new blank Edit landing page created in V31.71. The new Edit page layout, 16-column 26px grid, formatting, header, Grid toggle, and intentionally blank content are unchanged. EDIT from the new View no longer jumps directly to the new Edit page.
    Risk areas: App-mode Edit button routing only. Existing Edit implementation, new Edit layout, alternate View layout, Cards, roster data, persistence, Waha routing, Weapons, combat behavior, and CSV data remain unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.71\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.67\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

checks = [
    '<title>WH40k 11th V31.72</title>',
    'const APP_VERSION = "31.72";',
    "version: 'V31.72',",
    'CHANGE NOTE - WH40k_11th_V31.72',
    'if (appEditMode) {',
    'typeof npWindow.renderPage === "function"',
    'npWindow.renderPage("edit");',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('acceptance check failed: ' + ', '.join(missing))

out.write_text(text, encoding='utf-8')
print('Built V31.72: first Edit press opens legacy Edit; second press opens new Edit')
