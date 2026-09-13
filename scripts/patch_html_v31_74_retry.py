from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.73.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def once(old, new, label):
    global text
    n = text.count(old)
    if n != 1:
        raise SystemExit(f'{label}: expected 1 match, found {n}')
    text = text.replace(old, new, 1)


once('<title>WH40k 11th V31.73</title>', '<title>WH40k 11th V31.74</title>', 'title')
once('The current baseline is WH40k_11th_V31.73;', 'The current baseline is WH40k_11th_V31.74;', 'baseline')
once('const APP_VERSION = "31.73";', 'const APP_VERSION = "31.74";', 'APP_VERSION')
once("version: 'V31.73',", "version: 'V31.74',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
edit_pat = re.compile(r'(<iframe id="npEditFrame" class="np-view-frame" title="New Edit" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
em = edit_pat.search(text)
if not vm or not em:
    raise SystemExit('View/Edit iframe missing')
view_np = html.unescape(vm.group(2))
edit_np = html.unescape(em.group(2))

# Explicit shared row contract. The current View layout uses rows 7 and 20.
# Force the dormant Edit row classes to those same coordinates in both documents
# so future reuse cannot drift from View.
def force_unit_rows(doc, label):
    targets = {
        'view-unit-row-first': 7,
        'view-unit-row-second': 20,
        'edit-unit-row-first': 7,
        'edit-unit-row-second': 20,
    }
    for cls, row in targets.items():
        pattern = re.compile(r'(\.' + re.escape(cls) + r'\{grid-row:)\d+(\})')
        doc, n = pattern.subn(r'\g<1>' + str(row) + r'\2', doc, count=1)
        if n != 1:
            raise SystemExit(f'{label} {cls} row rule: expected 1 match, found {n}')
    return doc

view_np = force_unit_rows(view_np, 'View document')
edit_np = force_unit_rows(edit_np, 'Edit document')

# New View gets Unit data only from New Edit.
legacy_call = 'parent.getAlternateViewUnitData(index)'
new_edit_call = 'parent.getNewEditUnitData(index)'
if view_np.count(legacy_call) != 1:
    raise SystemExit(f'View legacy Unit call: expected 1 match, found {view_np.count(legacy_call)}')
view_np = view_np.replace(legacy_call, new_edit_call, 1)

# Render only the two Unit rows on New Edit. No other Old Edit feature migrates.
blank_edit = "if(p==='edit'){addViewHeader(f);const viewOnly=f.querySelector('.view-filter-toggle');if(viewOnly)viewOnly.remove()}"
live_edit = "if(p==='edit'){addViewHeader(f);const viewOnly=f.querySelector('.view-filter-toggle');if(viewOnly)viewOnly.remove();addEditUnit(f,'edit-unit-row-first','','','');addEditUnit(f,'edit-unit-row-second','','','')}"
if edit_np.count(blank_edit) != 1:
    raise SystemExit(f'blank Edit branch: expected 1 match, found {edit_np.count(blank_edit)}')
edit_np = edit_np.replace(blank_edit, live_edit, 1)

bridge = r'''
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
if edit_np.count('function renderPage(p){') != 1:
    raise SystemExit('Edit renderPage marker missing')
edit_np = edit_np.replace('function renderPage(p){', bridge + 'function renderPage(p){', 1)

post_view = "if(p==='view')requestAnimationFrame(refreshAlternateViewUnitsFromParent)"
post_both = "if(p==='view')requestAnimationFrame(refreshAlternateViewUnitsFromParent);if(p==='edit')requestAnimationFrame(refreshNewEditUnitsFromLegacy)"
if edit_np.count(post_view) != 1:
    raise SystemExit(f'Edit post-render refresh marker: expected 1 match, found {edit_np.count(post_view)}')
edit_np = edit_np.replace(post_view, post_both, 1)

# Verify authored alignment before encoding.
for doc, label in [(view_np, 'View'), (edit_np, 'Edit')]:
    for cls, row in [('view-unit-row-first',7),('view-unit-row-second',20),('edit-unit-row-first',7),('edit-unit-row-second',20)]:
        if f'.{cls}{{grid-row:{row}}}' not in doc:
            raise SystemExit(f'{label} alignment failed for {cls}')

# Write View then Edit back into outer app.
text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]
em = edit_pat.search(text)
if not em:
    raise SystemExit('Edit iframe missing after View writeback')
text = text[:em.start(2)] + html.escape(edit_np, quote=True) + text[em.end(2):]

# Parent-facing New Edit bridge. Deliberately no Old Edit fallback here.
marker = '    function selectAppMode(mode) {'
if text.count(marker) != 1:
    raise SystemExit('selectAppMode marker missing')
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
text = text.replace(marker, parent_bridge + marker, 1)

# Refresh New Edit from Old Edit/model whenever its separate screen opens.
old_open = '''          const newEditPageScreen = document.getElementById("newEditPageScreen");
          if (newEditPageScreen) newEditPageScreen.classList.add("active");
          activeAppScreen = "neweditpage";
          window.scrollTo({ top: 0, left: 0, behavior: "auto" });'''
new_open = '''          const newEditPageScreen = document.getElementById("newEditPageScreen");
          if (newEditPageScreen) newEditPageScreen.classList.add("active");
          activeAppScreen = "neweditpage";
          const npEditFrame = document.getElementById("npEditFrame");
          try {
            const editWindow = npEditFrame && npEditFrame.contentWindow;
            if (editWindow && typeof editWindow.refreshNewEditUnitsFromLegacy === "function") editWindow.refreshNewEditUnitsFromLegacy();
          } catch (_) {}
          window.scrollTo({ top: 0, left: 0, behavior: "auto" });'''
once(old_open, new_open, 'New Edit open refresh')

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.74
    Scope: Establish the temporary Unit-data chain Old Edit/model -> New Edit -> New View for the two Units currently used by New View. New Edit renders exactly two live Unit rows sourced from the legacy roster/Edit model and exposes those records to New View. New View no longer reads the legacy Unit bridge directly. View and Edit Unit 1/Unit 2 are explicitly locked to the same authored grid rows: 7 and 20. No additional legacy Edit functionality is migrated.
    Risk areas: New View/New Edit Unit bridge and the two aligned Unit rows only. Legacy Edit behavior, New View detail/Weapon behavior, Cards, persistence, Waha routing, combat behavior, and CSV data remain unchanged.
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

# Final architecture checks.
vm = view_pat.search(text)
em = edit_pat.search(text)
if not vm or not em:
    raise SystemExit('final iframe verification failed')
final_view = html.unescape(vm.group(2))
final_edit = html.unescape(em.group(2))
if legacy_call in final_view:
    raise SystemExit('New View still reads Old Edit directly')
if new_edit_call not in final_view:
    raise SystemExit('New View is not linked to New Edit')
if legacy_call not in final_edit:
    raise SystemExit('New Edit is not linked to Old Edit/model')
if "addEditUnit(f,'edit-unit-row-first','','','')" not in final_edit or "addEditUnit(f,'edit-unit-row-second','','','')" not in final_edit:
    raise SystemExit('New Edit Unit rows missing')
for doc, label in [(final_view,'View'),(final_edit,'Edit')]:
    if '.view-unit-row-first{grid-row:7}' not in doc or '.view-unit-row-second{grid-row:20}' not in doc:
        raise SystemExit(f'{label} View-row alignment failed')
    if '.edit-unit-row-first{grid-row:7}' not in doc or '.edit-unit-row-second{grid-row:20}' not in doc:
        raise SystemExit(f'{label} Edit-row alignment failed')

for required in ['<title>WH40k 11th V31.74</title>','const APP_VERSION = "31.74";',"version: 'V31.74',",'window.getNewEditUnitData = function(index)','CHANGE NOTE - WH40k_11th_V31.74']:
    if required not in text:
        raise SystemExit('acceptance check failed: ' + required)

out.write_text(text, encoding='utf-8')
print('Built V31.74: Old Edit -> New Edit -> New View, Units aligned at rows 7 and 20')
