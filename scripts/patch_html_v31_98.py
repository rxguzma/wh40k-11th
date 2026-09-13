from pathlib import Path
import html
import re

path = Path('WH40k_11th.html')
text = path.read_text(encoding='utf-8')


def once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


# Sequential release metadata.
once('<title>WH40k 11th V31.97</title>', '<title>WH40k 11th V31.98</title>', 'title')
once('The current baseline is WH40k_11th_V31.97;', 'The current baseline is WH40k_11th_V31.98;', 'baseline')
once('const APP_VERSION = "31.97";', 'const APP_VERSION = "31.98";', 'APP_VERSION')
once("version: 'V31.97',", "version: 'V31.98',", 'quality version')

# ---------------------------------------------------------------------------
# New View navigation: retire separate VIEW and EDIT buttons. The sheet defaults
# to VIEW, so the reciprocal M:N button says EDIT. In local EDIT mode it says
# VIEW. CARDS remains at O:P. K:L is intentionally empty.
# ---------------------------------------------------------------------------
view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('New View iframe missing')
view_np = html.unescape(vm.group(2))

nav_pat = re.compile(r"function addPageNavigation\(f,p\)\{.*?\}\nlet newViewHeaderLocked=", re.S)
nav_match = nav_pat.search(view_np)
if not nav_match:
    raise SystemExit('New View navigation function missing')

new_nav = r'''function addPageNavigation(f,p){
  const m=document.createElement('div');
  m.className='top-mode-buttons';

  const toggle=document.createElement('button');
  toggle.type='button';
  toggle.className='button-standard';
  toggle.style.gridColumn='2';
  toggle.textContent=p==='view'?'EDIT':'VIEW';
  toggle.setAttribute('aria-label',p==='view'?'Switch to Edit':'Switch to View');
  toggle.onclick=()=>renderPage(p==='view'?'edit':'view');
  m.appendChild(toggle);

  const cards=document.createElement('button');
  cards.type='button';
  cards.className='button-standard';
  cards.style.gridColumn='3';
  cards.textContent='CARDS';
  cards.setAttribute('aria-label','Cards');
  cards.onclick=()=>parent.UI.selectAppMode('cards');
  m.appendChild(cards);

  f.appendChild(m);
}
let newViewHeaderLocked='''
view_np = view_np[:nav_match.start()] + new_nav + view_np[nav_match.end():]

# Write the modified New View document back before outer-page cleanup.
text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

# ---------------------------------------------------------------------------
# Retire only the obsolete standalone New Edit page and its dedicated outer
# plumbing. Shared Edit classes/functions inside New View remain untouched.
# ---------------------------------------------------------------------------
edit_screen_pat = re.compile(
    r'\n\s*<div id="newEditPageScreen"[^>]*>\s*'
    r'<iframe id="npEditFrame"[^>]*srcdoc=".*?"></iframe>\s*'
    r'</div>\s*',
    re.S,
)
text, removed = edit_screen_pat.subn('\n', text, count=1)
if removed != 1:
    raise SystemExit(f'New Edit screen removal: expected 1 match, found {removed}')

# Remove the parent-facing bridges whose only purpose was to proxy through
# npEditFrame. The direct Alternate View/model bridges are deliberately kept.
for name, args in [
    ('getNewEditUnitData', r'index'),
    ('getNewEditRosterRows', r''),
    ('getNewEditHeaderData', r''),
]:
    pattern = rf'\n?    window\.{name} = function\({args}\) \{{\n.*?\n    \}};\n'
    text, count = re.subn(pattern, '\n', text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f'{name} bridge removal: expected 1 match, found {count}')

# V31.88 left a dedicated route to Old Edit behind. Unified EDIT has been local
# since V31.90, so the route is now dead and can be removed with the old page.
legacy_route_pat = re.compile(
    r'\n?    window\.openLegacyEditFromNewView = function\(\) \{\n.*?\n    \};\n',
    re.S,
)
text, removed = legacy_route_pat.subn('\n', text, count=1)
if removed != 1:
    raise SystemExit(f'openLegacyEditFromNewView removal: expected 1 match, found {removed}')

# Remove the old "leaving neweditpage" cleanup branch.
newedit_exit_pat = re.compile(
    r'\n?      if \(activeAppScreen === "neweditpage"\) \{\n.*?\n      \}\n\n',
    re.S,
)
text, removed = newedit_exit_pat.subn('\n', text, count=1)
if removed != 1:
    raise SystemExit(f'neweditpage exit removal: expected 1 match, found {removed}')

# The canonical parent Edit route must no longer have a second-press path to the
# deleted New Edit screen. Repeated Edit simply remains in the existing Edit.
edit_route_pat = re.compile(
    r'      if \(target === "edit"\) \{\n.*?\n      \}\n\n      if \(target === "view"\) \{',
    re.S,
)
edit_route = '''      if (target === "edit") {
        if (activeAppScreen === "cards") showArmyScreen({ commitCardsState: true });
        if (!appEditMode) setEditMode(true);
        return;
      }

      if (target === "view") {'''
text, route_count = edit_route_pat.subn(edit_route, text, count=1)
if route_count != 1:
    raise SystemExit(f'parent Edit route replacement: expected 1 match, found {route_count}')

# Release note.
note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.98
    Scope: Retire the obsolete standalone New Edit page after the View/Edit migration into New View. Remove its dedicated screen, iframe, proxy data bridges, second-press routing, and dead legacy route while preserving shared Edit styles/functions used by the unified New View EDIT mode. New View navigation is simplified to one reciprocal mode button at M:N and Cards at O:P, leaving K:L empty: VIEW is the default state and therefore shows EDIT; EDIT shows VIEW. Both states continue to render locally through renderPage without a page reload.
    Risk areas: New View header navigation and removal of dead standalone-New-Edit infrastructure only. Unified EDIT rows/actions, direct Alternate View/model bridges, New View lock/frozen snapshot, Version/Update/Download grid controls, Old Edit functionality, Cards, persistence, CSV data, Waha routing, and Probable remain unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.97\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

# Retain only the five newest detailed V31 notes.
notes = list(re.finditer(r'\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n', text, re.S))
for match in reversed(notes[5:]):
    text = text[:match.start()] + text[match.end():]

# ---------------------------------------------------------------------------
# Final acceptance checks.
# ---------------------------------------------------------------------------
vm = view_pat.search(text)
if not vm:
    raise SystemExit('New View iframe missing after cleanup')
final_view = html.unescape(vm.group(2))

required_view = [
    "toggle.style.gridColumn='2'",
    "cards.style.gridColumn='3'",
    "toggle.textContent=p==='view'?'EDIT':'VIEW'",
    "toggle.onclick=()=>renderPage(p==='view'?'edit':'view')",
    "cards.onclick=()=>parent.UI.selectAppMode('cards')",
    "function refreshUnifiedEdit",
    "parent.getAlternateViewRosterRows==='function'",
    "parent.getAlternateViewHeaderData==='function'",
    "renderPage('view');",
    ".new-view-version-toggle{grid-column:1/span 8;",
]
for value in required_view:
    if value not in final_view:
        raise SystemExit('V31.98 New View acceptance failed: ' + value)

for forbidden in [
    "[['view','VIEW'],['edit','EDIT'],['cards','CARDS']]",
    "parent.openLegacyEditFromNewView",
]:
    if forbidden in final_view:
        raise SystemExit('V31.98 old New View navigation remains: ' + forbidden)

required_outer = [
    '<title>WH40k 11th V31.98</title>',
    'The current baseline is WH40k_11th_V31.98;',
    'const APP_VERSION = "31.98";',
    "version: 'V31.98',",
    'window.getAlternateViewUnitData = function(index)',
    'window.getAlternateViewRosterRows = function()',
    'window.getAlternateViewHeaderData = function()',
    'CHANGE NOTE - WH40k_11th_V31.98',
]
for value in required_outer:
    if value not in text:
        raise SystemExit('V31.98 acceptance failed: ' + value)

for forbidden in [
    'id="newEditPageScreen"',
    'id="npEditFrame"',
    'newEditPageScreen',
    'npEditFrame',
    'activeAppScreen === "neweditpage"',
    'activeAppScreen = "neweditpage"',
    'window.getNewEditUnitData',
    'window.getNewEditRosterRows',
    'window.getNewEditHeaderData',
    'window.openLegacyEditFromNewView',
]:
    if forbidden in text:
        raise SystemExit('V31.98 obsolete New Edit infrastructure remains: ' + forbidden)

path.write_text(text, encoding='utf-8')
print('Built V31.98: standalone New Edit removed; M:N reciprocal VIEW/EDIT toggle; Cards O:P')
