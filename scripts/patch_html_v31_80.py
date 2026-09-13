from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.79.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


once('<title>WH40k 11th V31.79</title>', '<title>WH40k 11th V31.80</title>', 'title')
once('The current baseline is WH40k_11th_V31.79;', 'The current baseline is WH40k_11th_V31.80;', 'baseline')
once('const APP_VERSION = "31.79";', 'const APP_VERSION = "31.80";', 'APP_VERSION')
once("version: 'V31.79',", "version: 'V31.80',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('New View iframe missing')
view_np = html.unescape(vm.group(2))

# Make the title contract explicit: every visible title value is read from the
# New Edit header record only. Do not consume a preformatted summary string;
# points are read directly from New Edit just like the other title fields.
old_helper = r'''function refreshAlternateViewHeaderFromNewEdit(){
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
new_helper = r'''function refreshNewViewTitleFromNewEdit(){
  let data=null;
  try{data=parent&&typeof parent.getNewEditHeaderData==='function'?parent.getNewEditHeaderData():null}catch(_){data=null}
  const name=grid.querySelector('.top-roster-name');
  const detachments=grid.querySelector('.top-detachments');
  const disposition=grid.querySelector('.top-summary-disposition');
  const rest=grid.querySelector('.top-summary-rest');
  if(name)name.textContent=data?String(data.rosterName||''):'';
  if(detachments)detachments.textContent=data?String(data.detachments||''):'';
  if(disposition)disposition.textContent=data?String(data.disposition||''):'';
  if(rest)rest.textContent=data?`- ${String(data.points??0)} pts`:'';
  return Boolean(data);
}
window.refreshNewViewTitleFromNewEdit=refreshNewViewTitleFromNewEdit;
'''
if view_np.count(old_helper) != 1:
    raise SystemExit(f'New View title helper: expected 1 match, found {view_np.count(old_helper)}')
view_np = view_np.replace(old_helper, new_helper, 1)

old_post = "requestAnimationFrame(refreshAlternateViewHeaderFromNewEdit)"
new_post = "requestAnimationFrame(refreshNewViewTitleFromNewEdit)"
if view_np.count(old_post) != 1:
    raise SystemExit(f'New View title post-render refresh: expected 1 match, found {view_np.count(old_post)}')
view_np = view_np.replace(old_post, new_post, 1)

text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

# Update the outer screen-open refresh to the same exclusive title helper.
old_open = '''        if (npWindow && typeof npWindow.refreshAlternateViewHeaderFromNewEdit === "function") npWindow.refreshAlternateViewHeaderFromNewEdit();'''
new_open = '''        if (npWindow && typeof npWindow.refreshNewViewTitleFromNewEdit === "function") npWindow.refreshNewViewTitleFromNewEdit();'''
once(old_open, new_open, 'New View title screen-open refresh')

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.80
    Scope: Enforce the New View title source boundary. Every visible New View title value—roster name, Detachment list, Disposition, and points—is now read only from New Edit's header record through getNewEditHeaderData(). New View no longer consumes any preformatted legacy/global title summary or VP value, and its points text is formatted locally from New Edit's points field. Build-time checks explicitly reject direct Old Edit/model title access, Cards VP access, static roster title values, and the retired summaryRest dependency inside New View. Unit/Weapon data remains on its existing temporary legacy source and is not changed in this phase.
    Risk areas: New View title/header linkage only. New Edit's temporary upstream Old Edit/model feed, New View Unit/Weapon linkage, Cards scoring, persistence, CSV data, Waha routing, and Probable are unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.79\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.75\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

# Double-check the final New View title has exactly one data source: New Edit.
vm = view_pat.search(text)
if not vm:
    raise SystemExit('New View iframe missing after writeback')
final_view = html.unescape(vm.group(2))

if final_view.count("parent.getNewEditHeaderData()") != 1:
    raise SystemExit(f'New View title must have exactly one New Edit header read; found {final_view.count("parent.getNewEditHeaderData()")}')

for forbidden in [
    'parent.getAlternateViewHeaderData',
    'getAlternateViewHeaderData()',
    'getCardsTotalVpForRoster',
    'summaryRest',
    "n.textContent='Winning ORKS'",
    "d.textContent='Bully Boyz - Da Big Hunt - Wreckas'",
    "a.textContent='Priority Assets'",
    "z.textContent='- 1995 pts - 10 VPs'",
    'refreshAlternateViewHeaderFromNewEdit',
]:
    if forbidden in final_view:
        raise SystemExit('New View title has an alternate/retired dependency: ' + forbidden)

for required in [
    "if(name)name.textContent=data?String(data.rosterName||''):'';",
    "if(detachments)detachments.textContent=data?String(data.detachments||''):'';",
    "if(disposition)disposition.textContent=data?String(data.disposition||''):'';",
    "if(rest)rest.textContent=data?`- ${String(data.points??0)} pts`:'';",
    'window.refreshNewViewTitleFromNewEdit=refreshNewViewTitleFromNewEdit;',
    "parent.getAlternateViewUnitData(index)",
]:
    if required not in final_view:
        raise SystemExit('New View title/source acceptance check failed: ' + required)

# The parent bridge itself must return New Edit iframe-owned data and must not
# fall back directly to the Old Edit/model header bridge.
bridge_start = text.index('    window.getNewEditHeaderData = function() {')
bridge_end = text.index('\n\n    function selectAppMode(mode) {', bridge_start)
bridge = text[bridge_start:bridge_end]
for required in [
    'document.getElementById("npEditFrame")',
    'editWindow.getNewEditHeaderData()',
]:
    if required not in bridge:
        raise SystemExit('New Edit parent header bridge check failed: ' + required)
for forbidden in [
    'getAlternateViewHeaderData()',
    'getActiveRoster()',
    'getViewEditRoster()',
    'getRosterPoints(',
    'getCardsTotalVpForRoster(',
]:
    if forbidden in bridge:
        raise SystemExit('New View -> New Edit header bridge has forbidden fallback: ' + forbidden)

for required in [
    '<title>WH40k 11th V31.80</title>',
    'const APP_VERSION = "31.80";',
    "version: 'V31.80',",
    'CHANGE NOTE - WH40k_11th_V31.80',
]:
    if required not in text:
        raise SystemExit('version acceptance check failed: ' + required)

out.write_text(text, encoding='utf-8')
print('Built V31.80: New View title is exclusively sourced from New Edit')
