from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.73.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


replace_once('<title>WH40k 11th V31.73</title>', '<title>WH40k 11th V31.74</title>', 'title')
replace_once('The current baseline is WH40k_11th_V31.73;', 'The current baseline is WH40k_11th_V31.74;', 'baseline')
replace_once('const APP_VERSION = "31.73";', 'const APP_VERSION = "31.74";', 'APP_VERSION')
replace_once("version: 'V31.73',", "version: 'V31.74',", 'quality version')

# Extract the separate New View and New Edit documents.
view_pattern = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
edit_pattern = re.compile(r'(<iframe id="npEditFrame" class="np-view-frame" title="New Edit" srcdoc=")(.*?)("></iframe>)', re.S)
view_match = view_pattern.search(text)
edit_match = edit_pattern.search(text)
if not view_match:
    raise SystemExit('New View iframe not found')
if not edit_match:
    raise SystemExit('New Edit iframe not found')
view_np = html.unescape(view_match.group(2))
edit_np = html.unescape(edit_match.group(2))

# New View must no longer read the legacy/Old Edit roster bridge directly.
# Its two Unit rows now obtain their records only through New Edit.
old_view_source = "parent.getAlternateViewUnitData(index)"
new_view_source = "parent.getNewEditUnitData(index)"
if view_np.count(old_view_source) != 1:
    raise SystemExit(f'New View legacy Unit source: expected 1 match, found {view_np.count(old_view_source)}')
view_np = view_np.replace(old_view_source, new_view_source, 1)

# New Edit owns the two Unit records needed by New View. It remains intentionally
# minimal: only the existing Edit Unit rows are rendered; no legacy Edit feature
# is migrated. Old Edit remains the temporary upstream source through the
# existing getAlternateViewUnitData bridge.
old_edit_branch = "if(p==='edit'){addViewHeader(f);const viewOnly=f.querySelector('.view-filter-toggle');if(viewOnly)viewOnly.remove()}"
new_edit_branch = "if(p==='edit'){addViewHeader(f);const viewOnly=f.querySelector('.view-filter-toggle');if(viewOnly)viewOnly.remove();addEditUnit(f,'edit-unit-row-first','','','');addEditUnit(f,'edit-unit-row-second','','','')}"
if edit_np.count(old_edit_branch) != 1:
    raise SystemExit(f'blank New Edit branch: expected 1 match, found {edit_np.count(old_edit_branch)}')
edit_np = edit_np.replace(old_edit_branch, new_edit_branch, 1)

edit_bridge = r'''
function legacyUnitForNewEdit(index){
  try{return parent&&typeof parent.getAlternateViewUnitData==='function'?parent.getAlternateViewUnitData(index):null}catch(_){return null}
}
function refreshNewEditUnitsFromLegacy(){
  for(let index=0;index<2;index++){
    const row=grid.querySelector(index===0?'.edit-unit-row-first':'.edit-unit-row-second');
    if(!row)continue;
    const data=legacyUnitForNewEdit(index);
    if(!data){row.style.display='none';continue}
    row.style.display='grid';
    const name=row.querySelector('.edit-unit-name');
    if(name)name.textContent=String(data.name||'');
  }
  return Boolean(legacyUnitForNewEdit(0)||legacyUnitForNewEdit(1));
}
window.getNewEditUnitData=function(index){return legacyUnitForNewEdit(index)};
window.refreshNewEditUnitsFromLegacy=refreshNewEditUnitsFromLegacy;
'''
render_marker = 'function renderPage(p){'
if edit_np.count(render_marker) != 1:
    raise SystemExit(f'New Edit render marker: expected 1 match, found {edit_np.count(render_marker)}')
edit_np = edit_np.replace(render_marker, edit_bridge + render_marker, 1)

old_refresh = "if(p==='view')requestAnimationFrame(refreshAlternateViewUnitsFromParent)"
new_refresh = "if(p==='view')requestAnimationFrame(refreshAlternateViewUnitsFromParent);if(p==='edit')requestAnimationFrame(refreshNewEditUnitsFromLegacy)"
if edit_np.count(old_refresh) != 1:
    raise SystemExit(f'New Edit post-render refresh: expected 1 match, found {edit_np.count(old_refresh)}')
edit_np = edit_np.replace(old_refresh, new_refresh, 1)

# Hard alignment contract: the two Units use the exact same authored rows on
# New View and New Edit. These values must move together in future changes.
alignment_css = '.view-unit-row-first{grid-row:9}.view-unit-row-second{grid-row:20}.edit-unit-row-first{grid-row:9}.edit-unit-row-second{grid-row:20}'
if alignment_css not in view_np or alignment_css not in edit_np:
    raise SystemExit('View/Edit Unit row alignment contract missing')

# Write the modified iframe documents back into the outer app. Re-find the Edit
# iframe after View replacement because encoded srcdoc length changes offsets.
view_srcdoc = html.escape(view_np, quote=True)
text = text[:view_match.start(2)] + view_srcdoc + text[view_match.end(2):]
edit_match = edit_pattern.search(text)
if not edit_match:
    raise SystemExit('New Edit iframe missing after View update')
edit_srcdoc = html.escape(edit_np, quote=True)
text = text[:edit_match.start(2)] + edit_srcdoc + text[edit_match.end(2):]

# Parent bridge for New View. This bridge is intentionally allowed to talk only
# to npEditFrame; it has no legacy fallback. That keeps the dependency direction:
# Old Edit/model -> New Edit -> New View.
parent_marker = '    function selectAppMode(mode) {'
if text.count(parent_marker) != 1:
    raise SystemExit(f'parent bridge insertion marker: expected 1 match, found {text.count(parent_marker)}')
parent_bridge = '''    window.getNewEditUnitData = function(index) {
      const frame = document.getElementById("npEditFrame");
      try {
        const editWindow = frame && frame.contentWindow;
        return editWindow && typeof editWindow.getNewEditUnitData === "function"
          ? editWindow.getNewEditUnitData(index)
          : null;
      } catch (_) {
        return null;
      }
    };

'''
text = text.replace(parent_marker, parent_bridge + parent_marker, 1)

# Every time the separate New Edit page opens, refresh its two rows from Old
# Edit so New Edit stays current before New View consumes those records.
old_open_edit = '''          const newEditPageScreen = document.getElementById("newEditPageScreen");
          if (newEditPageScreen) newEditPageScreen.classList.add("active");
          activeAppScreen = "neweditpage";
          window.scrollTo({ top: 0, left: 0, behavior: "auto" });'''
new_open_edit = '''          const newEditPageScreen = document.getElementById("newEditPageScreen");
          if (newEditPageScreen) newEditPageScreen.classList.add("active");
          activeAppScreen = "neweditpage";
          const npEditFrame = document.getElementById("npEditFrame");
          try {
            const editWindow = npEditFrame && npEditFrame.contentWindow;
            if (editWindow && typeof editWindow.refreshNewEditUnitsFromLegacy === "function") editWindow.refreshNewEditUnitsFromLegacy();
          } catch (_) {}
          window.scrollTo({ top: 0, left: 0, behavior: "auto" });'''
replace_once(old_open_edit, new_open_edit, 'New Edit refresh on open')

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.74
    Scope: Establish the temporary data dependency Old Edit/model -> New Edit -> New View for the two Unit rows currently used by New View. New Edit now renders exactly two live Unit rows sourced from the existing legacy roster/Edit model and exposes those Unit records to New View. New View no longer reads the legacy Unit bridge directly. Unit 1 and Unit 2 remain locked to the exact same authored grid rows on both pages: rows 9 and 20. No other legacy Edit functionality is migrated.
    Risk areas: New View/New Edit Unit data bridge and the two aligned Unit rows only. Existing legacy Edit behavior, New View detail/Weapon behavior, Cards, persistence, Waha routing, combat behavior, and CSV data remain unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.73\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.69\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

# Static acceptance checks, including the dependency direction and row lock.
checks = [
    '<title>WH40k 11th V31.74</title>',
    'const APP_VERSION = "31.74";',
    "version: 'V31.74',",
    'id="newPageScreen" class="screen np-view-screen"',
    'id="npViewFrame" class="np-view-frame" title="Alternate View"',
    'id="newEditPageScreen" class="screen np-view-screen"',
    'id="npEditFrame" class="np-view-frame" title="New Edit"',
    'window.getNewEditUnitData = function(index)',
    'refreshNewEditUnitsFromLegacy',
    'CHANGE NOTE - WH40k_11th_V31.74',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('acceptance check failed: ' + ', '.join(missing))

# Re-read both encoded iframe documents to verify the architecture after writeback.
vm = view_pattern.search(text)
em = edit_pattern.search(text)
if not vm or not em:
    raise SystemExit('final iframe verification failed')
final_view = html.unescape(vm.group(2))
final_edit = html.unescape(em.group(2))
if 'parent.getAlternateViewUnitData(index)' in final_view:
    raise SystemExit('New View still depends directly on Old Edit Unit bridge')
if 'parent.getNewEditUnitData(index)' not in final_view:
    raise SystemExit('New View does not depend on New Edit Unit bridge')
if "parent.getAlternateViewUnitData(index)" not in final_edit:
    raise SystemExit('New Edit is not linked to Old Edit Unit bridge')
if "addEditUnit(f,'edit-unit-row-first','','','')" not in final_edit or "addEditUnit(f,'edit-unit-row-second','','','')" not in final_edit:
    raise SystemExit('New Edit two Unit rows missing')
if alignment_css not in final_view or alignment_css not in final_edit:
    raise SystemExit('final View/Edit Unit alignment check failed')

out.write_text(text, encoding='utf-8')
print('Built V31.74: Old Edit -> New Edit -> New View for two row-aligned Units')
