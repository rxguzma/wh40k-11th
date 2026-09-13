from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.77.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


once('<title>WH40k 11th V31.77</title>', '<title>WH40k 11th V31.78</title>', 'title')
once('The current baseline is WH40k_11th_V31.77;', 'The current baseline is WH40k_11th_V31.78;', 'baseline')
once('const APP_VERSION = "31.77";', 'const APP_VERSION = "31.78";', 'APP_VERSION')
once("version: 'V31.77',", "version: 'V31.78',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('New View iframe missing')
view_np = html.unescape(vm.group(2))

# New View title values are now owned by New Edit. Remove all static roster title
# content from the View iframe; the visual elements remain unchanged.
static_header_replacements = [
    ("n.textContent='Winning ORKS'", "n.textContent=''"),
    ("d.textContent='Bully Boyz - Da Big Hunt - Wreckas'", "d.textContent=''"),
    ("a.textContent='Priority Assets'", "a.textContent=''"),
    ("z.textContent='- 1995 pts - 10 VPs'", "z.textContent=''"),
]
for old, new in static_header_replacements:
    if view_np.count(old) != 1:
        raise SystemExit(f'New View static title marker missing: {old}')
    view_np = view_np.replace(old, new, 1)

# Title-only bridge for this phase. Unit/Weapon data remains on its current source.
header_helper = r'''
function refreshAlternateViewHeaderFromNewEdit(){
  let data=null;
  try{data=parent&&typeof parent.getNewEditHeaderData==='function'?parent.getNewEditHeaderData():null}catch(_){data=null}
  const name=grid.querySelector('.top-roster-name');
  const detachments=grid.querySelector('.top-detachments');
  const disposition=grid.querySelector('.top-summary-disposition');
  const rest=grid.querySelector('.top-summary-rest');
  if(name)name.textContent=data?String(data.rosterName||''):'';
  if(detachments)detachments.textContent=data?String(data.detachments||''):'';
  if(disposition)disposition.textContent=data?String(data.disposition||''):'';
  if(rest)rest.textContent=data?String(data.summaryRest||''):'';
  return Boolean(data);
}
window.refreshAlternateViewHeaderFromNewEdit=refreshAlternateViewHeaderFromNewEdit;
'''
marker = 'function renderPage(p){'
if view_np.count(marker) != 1:
    raise SystemExit('New View renderPage marker missing')
view_np = view_np.replace(marker, header_helper + marker, 1)

old_post = "if(p==='view')requestAnimationFrame(refreshAlternateViewUnitsFromParent)"
new_post = "if(p==='view'){requestAnimationFrame(refreshAlternateViewHeaderFromNewEdit);requestAnimationFrame(refreshAlternateViewUnitsFromParent)}"
if view_np.count(old_post) != 1:
    raise SystemExit(f'New View post-render marker: expected 1 match, found {view_np.count(old_post)}')
view_np = view_np.replace(old_post, new_post, 1)

# Write New View iframe back.
text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

# Make the existing New Edit header bridge self-refresh before returning data.
# This keeps the title source as New Edit even when New Edit has not been opened yet.
old_parent_bridge = '''    window.getNewEditHeaderData = function() {
      const frame = document.getElementById("npEditFrame");
      try {
        const editWindow = frame && frame.contentWindow;
        return editWindow && typeof editWindow.getNewEditHeaderData === "function"
          ? editWindow.getNewEditHeaderData()
          : null;
      } catch (_) {
        return null;
      }
    };'''
new_parent_bridge = '''    window.getNewEditHeaderData = function() {
      const frame = document.getElementById("npEditFrame");
      try {
        const editWindow = frame && frame.contentWindow;
        if (editWindow && typeof editWindow.refreshNewEditUnitsFromLegacy === "function") editWindow.refreshNewEditUnitsFromLegacy();
        return editWindow && typeof editWindow.getNewEditHeaderData === "function"
          ? editWindow.getNewEditHeaderData()
          : null;
      } catch (_) {
        return null;
      }
    };'''
once(old_parent_bridge, new_parent_bridge, 'New Edit header parent bridge')

# Refresh title whenever the already-loaded New View screen becomes visible.
old_open_refresh = '''        if (npWindow && typeof npWindow.refreshAlternateViewUnitsFromParent === "function") npWindow.refreshAlternateViewUnitsFromParent();'''
new_open_refresh = '''        if (npWindow && typeof npWindow.refreshAlternateViewHeaderFromNewEdit === "function") npWindow.refreshAlternateViewHeaderFromNewEdit();
        if (npWindow && typeof npWindow.refreshAlternateViewUnitsFromParent === "function") npWindow.refreshAlternateViewUnitsFromParent();'''
once(old_open_refresh, new_open_refresh, 'New View open refresh')

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.78
    Scope: Link every visible New View title/header value to the staged New Edit title record. New View roster name, selected Detachment list, active Disposition, and roster points now read only through New Edit's header contract; the old static title strings are removed from New View. New Edit refreshes its temporary Old Edit/model-fed title record on demand before returning it, so New View receives current title data even if New Edit was not opened first. This phase changes title/header linkage only: New View Unit/Weapon data remains on its existing source until separately approved. VP remains excluded from the title contract.
    Risk areas: New View title/header data source and refresh only. Unit/Weapon linkage, Old Edit behavior, New Edit Unit data, Cards, persistence, CSV data, Waha routing, and Probable are unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.77\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.73\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

# Acceptance: title must depend on New Edit, while Units must remain deliberately unlinked.
vm = view_pat.search(text)
if not vm:
    raise SystemExit('New View iframe missing after writeback')
final_view = html.unescape(vm.group(2))
for forbidden in [
    "n.textContent='Winning ORKS'",
    "d.textContent='Bully Boyz - Da Big Hunt - Wreckas'",
    "a.textContent='Priority Assets'",
    "z.textContent='- 1995 pts - 10 VPs'",
]:
    if forbidden in final_view:
        raise SystemExit('static New View title remains: ' + forbidden)
for required in [
    "parent.getNewEditHeaderData()",
    "window.refreshAlternateViewHeaderFromNewEdit=refreshAlternateViewHeaderFromNewEdit;",
    "parent.getAlternateViewUnitData(index)",
    '<title>WH40k 11th V31.78</title>',
    'const APP_VERSION = "31.78";',
    "version: 'V31.78',",
    'CHANGE NOTE - WH40k_11th_V31.78',
]:
    if required not in final_view and required not in text:
        raise SystemExit('acceptance check failed: ' + required)
if 'parent.getNewEditUnitData(index)' in final_view:
    raise SystemExit('Unit data was linked to New Edit before approval')

out.write_text(text, encoding='utf-8')
print('Built V31.78: New View title linked entirely to New Edit title data')
