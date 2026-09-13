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
once('<title>WH40k 11th V31.87</title>', '<title>WH40k 11th V31.88</title>', 'title')
once('The current baseline is WH40k_11th_V31.87;', 'The current baseline is WH40k_11th_V31.88;', 'baseline')
once('const APP_VERSION = "31.87";', 'const APP_VERSION = "31.88";', 'APP_VERSION')
once("version: 'V31.87',", "version: 'V31.88',", 'quality version')

# Decode New View only. New Edit remains physically present and untouched in
# this pass, but New View must stop using it as a data or navigation dependency.
view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('New View iframe missing')
view_np = html.unescape(vm.group(2))

# Bypass New Edit's forwarding cache. Read the canonical Old Edit/model bridges
# directly. These records already include roster order, Units, Stats, Abilities,
# Weapons, Tags, Waha URL, points, Detachments, and Disposition.
replacements = [
    ('parent.getNewEditRosterRows', 'parent.getAlternateViewRosterRows', 'New View roster-row source'),
    ('parent.getNewEditHeaderData', 'parent.getAlternateViewHeaderData', 'New View header source'),
    ('parent.getNewEditUnitData', 'parent.getAlternateViewUnitData', 'New View Unit source'),
]
for old, new, label in replacements:
    count = view_np.count(old)
    if count:
        view_np = view_np.replace(old, new)
    if old in view_np:
        raise SystemExit(f'{label}: old dependency remains')

# Keep naming aligned with the new source boundary when that helper exists.
view_np = view_np.replace('refreshNewViewTitleFromNewEdit', 'refreshNewViewTitleFromLegacy')

# New View EDIT must always open the existing/legacy Edit surface. Do not route
# through the general second-press behavior that opens New Edit.
old_nav = "b.onclick=()=>parent.UI.selectAppMode(t);"
new_nav = "b.onclick=()=>{if(t==='edit'&&parent&&typeof parent.openLegacyEditFromNewView==='function')parent.openLegacyEditFromNewView();else parent.UI.selectAppMode(t)};"
if view_np.count(old_nav) != 1:
    raise SystemExit(f'New View navigation handler: expected 1 match, found {view_np.count(old_nav)}')
view_np = view_np.replace(old_nav, new_nav, 1)

# Write New View back before adding the parent route.
view_srcdoc = html.escape(view_np, quote=True)
text = text[:vm.start(2)] + view_srcdoc + text[vm.end(2):]

# Dedicated parent route from New View to existing Edit. If Edit mode is already
# active, simply reveal the existing roster/Edit surface; otherwise enter Edit.
# New Edit remains intact for the next deletion pass but is never touched here.
select_marker = '\n\n    function selectAppMode(mode) {'
if text.count(select_marker) != 1:
    raise SystemExit(f'selectAppMode marker: expected 1 match, found {text.count(select_marker)}')
if 'window.openLegacyEditFromNewView = function()' in text:
    raise SystemExit('legacy Edit route already exists')
legacy_route = '''

    window.openLegacyEditFromNewView = function() {
      const newPageScreen = document.getElementById("newPageScreen");
      const newEditPageScreen = document.getElementById("newEditPageScreen");
      const rosterScreen = document.getElementById("rosterScreen");
      if (newPageScreen) newPageScreen.classList.remove("active");
      if (newEditPageScreen) newEditPageScreen.classList.remove("active");
      if (rosterScreen) rosterScreen.classList.add("active");
      document.body.classList.remove("np-view-screen-active");
      activeAppScreen = "army";
      if (!appEditMode) setEditMode(true);
      window.scrollTo({ top: 0, left: 0, behavior: "auto" });
    };'''
text = text.replace(select_marker, legacy_route + select_marker, 1)

# Release note.
note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.88
    Scope: Remove New Edit from New View's runtime dependency chain. New View now reads its header and ordered roster rows directly from the existing Old Edit/model bridges instead of getNewEditHeaderData/getNewEditRosterRows/getNewEditUnitData. New View's EDIT button now opens the existing Old Edit surface directly through openLegacyEditFromNewView. New Edit remains physically present but is no longer required by New View, allowing it to be deleted in the next pass without changing New View data behavior.
    Risk areas: New View data-source boundary and New View-to-Old Edit navigation only. New Edit itself, Old Edit functionality, Cards, persistence, CSV data, Waha routing, Probable, and unrelated UI remain unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.87\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

# Retain only the five newest V31 change-note blocks.
notes = list(re.finditer(r'\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n', text, re.S))
for match in reversed(notes[5:]):
    text = text[:match.start()] + text[match.end():]

# Final checks against the decoded New View document.
vm = view_pat.search(text)
if not vm:
    raise SystemExit('New View iframe missing after patch')
final_view = html.unescape(vm.group(2))
required_view = [
    "parent.getAlternateViewRosterRows==='function'",
    "parent.getAlternateViewHeaderData==='function'",
    "typeof parent.openLegacyEditFromNewView==='function'",
]
for required in required_view:
    if required not in final_view:
        raise SystemExit(f'New View direct-legacy acceptance failed: {required}')
if 'parent.getNewEdit' in final_view:
    raise SystemExit('New View still contains a New Edit data dependency')

required_outer = [
    '<title>WH40k 11th V31.88</title>',
    'const APP_VERSION = "31.88";',
    "version: 'V31.88',",
    'window.openLegacyEditFromNewView = function()',
    'id="newEditPageScreen" class="screen np-view-screen"',
    'id="npEditFrame" class="np-view-frame" title="New Edit"',
    'CHANGE NOTE - WH40k_11th_V31.88',
]
for required in required_outer:
    if required not in text:
        raise SystemExit(f'V31.88 acceptance failed: {required}')

path.write_text(text, encoding='utf-8')
print('Built V31.88: New View reads Old Edit/model directly and EDIT opens Old Edit')
