from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.72.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


replace_once('<title>WH40k 11th V31.72</title>', '<title>WH40k 11th V31.73</title>', 'title')
replace_once('The current baseline is WH40k_11th_V31.72;', 'The current baseline is WH40k_11th_V31.73;', 'baseline')
replace_once('const APP_VERSION = "31.72";', 'const APP_VERSION = "31.73";', 'APP_VERSION')
replace_once("version: 'V31.72',", "version: 'V31.73',", 'quality version')

# Extract the approved alternate View document. Keep the View iframe View-only,
# then clone its exact phone/grid design into a separate Edit iframe.
frame_pattern = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
match = frame_pattern.search(text)
if not match:
    raise SystemExit('alternate View iframe not found')
view_np = html.unescape(match.group(2))

old_view_nav = "b.onclick=()=>{if(p==='edit'&&t==='view')renderPage('view');else if(p==='edit'&&t==='edit')return;else parent.UI.selectAppMode(t)};"
new_view_nav = "b.onclick=()=>parent.UI.selectAppMode(t);"
if view_np.count(old_view_nav) != 1:
    raise SystemExit(f'View navigation reset: expected 1 match, found {view_np.count(old_view_nav)}')
view_np = view_np.replace(old_view_nav, new_view_nav, 1)

# Build the new Edit document as its own document. It uses the same approved
# styles/grid/header but starts on the intentionally blank Edit landing branch.
edit_np = view_np
if edit_np.count(new_view_nav) != 1:
    raise SystemExit(f'Edit navigation source: expected 1 match, found {edit_np.count(new_view_nav)}')
edit_np = edit_np.replace(new_view_nav, "b.onclick=()=>{if(t==='edit')return;parent.UI.selectAppMode(t)};", 1)
terminal = "renderPage('view');"
pos = edit_np.rfind(terminal)
if pos < 0:
    raise SystemExit('terminal View render not found in cloned Edit document')
edit_np = edit_np[:pos] + "renderPage('edit');" + edit_np[pos + len(terminal):]

required_edit = [
    "if(p==='edit'){addViewHeader(f);const viewOnly=f.querySelector('.view-filter-toggle');if(viewOnly)viewOnly.remove()}",
    "grid-template-columns:repeat(16,var(--cell))",
    "--cell:26px",
    "grid-toggle",
    "renderPage('edit');",
]
missing_edit = [value for value in required_edit if value not in edit_np]
if missing_edit:
    raise SystemExit('new Edit document check failed: ' + ', '.join(missing_edit))

# Update the existing View iframe so it no longer internally owns Edit routing.
view_srcdoc = html.escape(view_np, quote=True)
text = text[:match.start(2)] + view_srcdoc + text[match.end(2):]

# Add a genuinely separate Edit screen/container with its own iframe/document.
edit_srcdoc = html.escape(edit_np, quote=True)
view_screen_pattern = re.compile(
    r'(<div id="newPageScreen" class="screen np-view-screen" aria-label="Alternate View page">\s*<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=".*?"></iframe>\s*</div>)',
    re.S,
)
view_screen_match = view_screen_pattern.search(text)
if not view_screen_match:
    raise SystemExit('alternate View screen container not found')
new_edit_screen = (
    '\n\n  <div id="newEditPageScreen" class="screen np-view-screen" aria-label="New Edit page">\n'
    f'    <iframe id="npEditFrame" class="np-view-frame" title="New Edit" srcdoc="{edit_srcdoc}"></iframe>\n'
    '  </div>'
)
text = text[:view_screen_match.end()] + new_edit_screen + text[view_screen_match.end():]

# Leaving the separate Edit page must deactivate its own screen before normal
# View/Cards/Edit routing continues.
select_marker = '''      if (target === "view" && activeAppScreen === "newpage") {'''
if text.count(select_marker) != 1:
    raise SystemExit(f'selectAppMode insertion marker: expected 1 match, found {text.count(select_marker)}')
new_edit_exit = '''      if (activeAppScreen === "neweditpage") {
        const newEditPageScreen = document.getElementById("newEditPageScreen");
        const rosterScreen = document.getElementById("rosterScreen");
        if (newEditPageScreen) newEditPageScreen.classList.remove("active");
        if (rosterScreen) rosterScreen.classList.add("active");
        document.body.classList.remove("np-view-screen-active");
        activeAppScreen = "army";
      }

'''
text = text.replace(select_marker, new_edit_exit + select_marker, 1)

# Second Edit press opens the separate Edit screen. No call into npViewFrame and
# no renderPage('edit') inside the View page is used anymore.
old_second_edit = '''        if (appEditMode) {
          showNewPageScreen();
          const npFrame = document.getElementById("npViewFrame");
          try {
            const npWindow = npFrame && npFrame.contentWindow;
            if (npWindow && typeof npWindow.renderPage === "function") npWindow.renderPage("edit");
          } catch (_) {}
          return;
        }'''
new_second_edit = '''        if (appEditMode) {
          showNewPageScreen();
          if (newPageScreen) newPageScreen.classList.remove("active");
          const newEditPageScreen = document.getElementById("newEditPageScreen");
          if (newEditPageScreen) newEditPageScreen.classList.add("active");
          activeAppScreen = "neweditpage";
          window.scrollTo({ top: 0, left: 0, behavior: "auto" });
          return;
        }'''
replace_once(old_second_edit, new_second_edit, 'second Edit routing')

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.73
    Scope: Replace the temporary shared-iframe Edit state with a genuinely separate new Edit page. Add newEditPageScreen with its own npEditFrame document, using the same approved 16-column 26px phone grid, typography, colors, spacing, header, navigation, and Grid toggle as the new View surface while remaining intentionally blank. The existing new View page stays in newPageScreen/npViewFrame and is View-only again. Existing/legacy Edit remains the first Edit press; pressing Edit a second time opens the separate new Edit screen.
    Risk areas: Second-press Edit routing and the new separate Edit screen only. Existing Edit content/functionality, new View content/functionality, Cards, roster data, persistence, Waha routing, Weapons, combat behavior, and CSV data remain unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.72\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.68\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

checks = [
    '<title>WH40k 11th V31.73</title>',
    'const APP_VERSION = "31.73";',
    "version: 'V31.73',",
    'id="newPageScreen" class="screen np-view-screen"',
    'id="npViewFrame" class="np-view-frame" title="Alternate View"',
    'id="newEditPageScreen" class="screen np-view-screen"',
    'id="npEditFrame" class="np-view-frame" title="New Edit"',
    'activeAppScreen = "neweditpage";',
    'CHANGE NOTE - WH40k_11th_V31.73',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('acceptance check failed: ' + ', '.join(missing))
if 'npWindow.renderPage("edit")' in text:
    raise SystemExit('old shared View/Edit iframe routing still present')

out.write_text(text, encoding='utf-8')
print('Built V31.73: separate new Edit screen with its own iframe and grid')
