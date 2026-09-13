from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.75.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


once('<title>WH40k 11th V31.75</title>', '<title>WH40k 11th V31.76</title>', 'title')
once('The current baseline is WH40k_11th_V31.75;', 'The current baseline is WH40k_11th_V31.76;', 'baseline')
once('const APP_VERSION = "31.75";', 'const APP_VERSION = "31.76";', 'APP_VERSION')
once("version: 'V31.75',", "version: 'V31.76',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
edit_pat = re.compile(r'(<iframe id="npEditFrame" class="np-view-frame" title="New Edit" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
em = edit_pat.search(text)
if not vm or not em:
    raise SystemExit('View/Edit iframe missing')
view_np = html.unescape(vm.group(2))
edit_np = html.unescape(em.group(2))

# PHASE BOUNDARY: New View is intentionally NOT linked to New Edit yet.
# Restore its current legacy/model Unit source until the user explicitly approves
# the final New Edit -> New View link in a later phase.
new_edit_call = 'parent.getNewEditUnitData(index)'
legacy_call = 'parent.getAlternateViewUnitData(index)'
if view_np.count(new_edit_call) != 1:
    raise SystemExit(f'New View staged Unit source: expected 1 match, found {view_np.count(new_edit_call)}')
view_np = view_np.replace(new_edit_call, legacy_call, 1)

# New Edit must contain/own a complete copy of every Unit record New View currently
# needs. Render the same read-only profile/detail/Weapon surface inside New Edit so
# the staged data can be inspected before New View is linked to it.
old_edit_branch = "if(p==='edit'){addViewHeader(f);const viewOnly=f.querySelector('.view-filter-toggle');if(viewOnly)viewOnly.remove();addEditUnit(f,'edit-unit-row-first','','','');addEditUnit(f,'edit-unit-row-second','','','')}"
new_edit_branch = "if(p==='edit'){addViewHeader(f);const viewOnly=f.querySelector('.view-filter-toggle');if(viewOnly)viewOnly.remove();addViewStatHeader(f);addViewUnit(f,'view-unit-row-first','','',['','','','','','']);addViewUnit(f,'view-unit-row-second','','',['','','','','','']);addExpandedUnitMock(f)}"
if edit_np.count(old_edit_branch) != 1:
    raise SystemExit(f'New Edit render branch: expected 1 match, found {edit_np.count(old_edit_branch)}')
edit_np = edit_np.replace(old_edit_branch, new_edit_branch, 1)

# Remove prototype/static header values from the New Edit document. They are
# populated from Old Edit/model data during refresh instead.
static_header_replacements = [
    ("n.textContent='Winning ORKS'", "n.textContent=''"),
    ("d.textContent='Bully Boyz - Da Big Hunt - Wreckas'", "d.textContent=''"),
    ("a.textContent='Priority Assets'", "a.textContent=''"),
    ("z.textContent='- 1995 pts - 10 VPs'", "z.textContent=''"),
]
for old, new in static_header_replacements:
    if edit_np.count(old) != 1:
        raise SystemExit(f'New Edit static header marker missing: {old}')
    edit_np = edit_np.replace(old, new, 1)

old_bridge = r'''function legacyUnitForNewEdit(index){
  try{return parent&&typeof parent.getAlternateViewUnitData==='function'?parent.getAlternateViewUnitData(index):null}catch(_){return null}
}
function refreshNewEditUnitsFromLegacy(){
  const start=typeof FIRST_UNIT_ROW==='number'?FIRST_UNIT_ROW:7;
  for(let index=0;index<2;index++){
    const row=grid.querySelector(index===0?'.edit-unit-row-first':'.edit-unit-row-second');
    if(!row)continue;
    const data=legacyUnitForNewEdit(index);
    if(!data){row.style.display='none';continue}
    row.style.gridRow=String(start+index);
    row.style.display='grid';
    const name=row.querySelector('.edit-unit-name');
    if(name)name.textContent=String(data.name||'');
  }
  return Boolean(legacyUnitForNewEdit(0)||legacyUnitForNewEdit(1));
}
window.getNewEditUnitData=function(index){return legacyUnitForNewEdit(index)};
window.refreshNewEditUnitsFromLegacy=refreshNewEditUnitsFromLegacy;
'''
new_bridge = r'''let newEditHeaderData=null;
function legacyHeaderForNewEdit(){
  try{return parent&&typeof parent.getAlternateViewHeaderData==='function'?parent.getAlternateViewHeaderData():null}catch(_){return null}
}
function refreshNewEditHeaderFromLegacy(){
  const data=legacyHeaderForNewEdit();
  newEditHeaderData=data?{
    rosterName:String(data.rosterName||''),
    detachments:String(data.detachments||''),
    disposition:String(data.disposition||''),
    points:Number(data.points)||0,
    vp:Number(data.vp)||0,
    summaryRest:String(data.summaryRest||'')
  }:null;
  const name=grid.querySelector('.top-roster-name');
  const detachments=grid.querySelector('.top-detachments');
  const disposition=grid.querySelector('.top-summary-disposition');
  const rest=grid.querySelector('.top-summary-rest');
  if(name)name.textContent=newEditHeaderData?newEditHeaderData.rosterName:'';
  if(detachments)detachments.textContent=newEditHeaderData?newEditHeaderData.detachments:'';
  if(disposition)disposition.textContent=newEditHeaderData?newEditHeaderData.disposition:'';
  if(rest)rest.textContent=newEditHeaderData?newEditHeaderData.summaryRest:'';
  return Boolean(newEditHeaderData);
}
function refreshNewEditUnitsFromLegacy(){
  const ok=refreshAlternateViewUnitsFromParent();
  refreshNewEditHeaderFromLegacy();
  return ok;
}
window.getNewEditUnitData=function(index){
  const clean=Math.max(0,Number(index)||0);
  return unitDataByIndex[clean]||null;
};
window.getNewEditHeaderData=function(){return newEditHeaderData};
window.refreshNewEditUnitsFromLegacy=refreshNewEditUnitsFromLegacy;
'''
if edit_np.count(old_bridge) != 1:
    raise SystemExit(f'New Edit legacy staging bridge: expected 1 match, found {edit_np.count(old_bridge)}')
edit_np = edit_np.replace(old_bridge, new_bridge, 1)

# The cloned View controller inside New Edit already reads the complete legacy
# Unit record (count/stats/Waha/core abilities/Weapons/tags/scope) into
# unitDataByIndex and renders its detail/Weapon panel on Unit tap.
for required in [
    "parent.getAlternateViewUnitData(index)",
    "let unitDataByIndex=[null,null];",
    "const weapons=data&&Array.isArray(data.weapons)?data.weapons:[];",
    "const coreAbilities=Array.isArray(data.coreAbilities)?data.coreAbilities:[];",
    "count.textContent='x'+String(data.count??1);",
    "window.getNewEditUnitData=function(index)",
    "window.getNewEditHeaderData=function(){return newEditHeaderData};",
]:
    if required not in edit_np:
        raise SystemExit('New Edit complete-data check failed: ' + required)

# Write View then Edit back into the outer app.
text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]
em = edit_pat.search(text)
if not em:
    raise SystemExit('Edit iframe missing after View writeback')
text = text[:em.start(2)] + html.escape(edit_np, quote=True) + text[em.end(2):]

# Old Edit/model header bridge. This is the temporary upstream source for New Edit
# in this phase. New Edit stores the returned strings/numbers locally; New View is
# deliberately not connected to them yet.
parent_marker = '    window.getNewEditUnitData = function(index) {'
if text.count(parent_marker) != 1:
    raise SystemExit('New Edit parent bridge marker missing')
header_bridge = '''    window.getAlternateViewHeaderData = function() {
      const roster = appEditMode && viewEditRosterDraft ? getViewEditRoster() : getActiveRoster();
      if (!roster) return null;
      reconcileRosterSelectedDispositionForUi(roster);
      const detachmentNames = getSelectedDetachmentNames(roster);
      const rosterDisposition = RosterModel.normalizeDisposition(roster.selectedDisposition);
      const requestedOverride = RosterModel.normalizeDisposition(UI.getRosterDispositionOverride(roster));
      const selectedDisposition = requestedOverride && requestedOverride !== rosterDisposition
        ? requestedOverride
        : rosterDisposition;
      const points = getRosterPoints(roster);
      const vp = getCardsTotalVpForRoster(roster);
      return {
        rosterName: String(roster.name || "").trim() || "Army",
        detachments: detachmentNames.join(" - "),
        disposition: selectedDisposition || (detachmentNames.length ? "Disposition?" : ""),
        points,
        vp,
        summaryRest: `- ${points} pts - ${vp} VPs`
      };
    };

'''
text = text.replace(parent_marker, header_bridge + parent_marker, 1)

# Expose New Edit's locally staged header record for the later linking phase.
new_edit_parent_bridge = '''    window.getNewEditHeaderData = function() {
      const frame = document.getElementById("npEditFrame");
      try {
        const editWindow = frame && frame.contentWindow;
        return editWindow && typeof editWindow.getNewEditHeaderData === "function"
          ? editWindow.getNewEditHeaderData()
          : null;
      } catch (_) {
        return null;
      }
    };

'''
select_marker = '    function selectAppMode(mode) {'
if text.count(select_marker) != 1:
    raise SystemExit('selectAppMode marker missing')
text = text.replace(select_marker, new_edit_parent_bridge + select_marker, 1)

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.76
    Scope: Stage the complete current New View data contract inside the separate New Edit page without linking New View to it yet. New Edit now copies from the existing Old Edit/model source and visibly renders the dynamic roster header, Unit count/profile stats, Waha/core-ability detail, and Weapon rows with stats, Tags, and scope for the first two Units. Unit detail/Weapon data is inspectable by opening a Unit in New Edit. New Edit stores those copied Unit records in its own unitDataByIndex array plus a local newEditHeaderData record and exposes both for the later linking phase. New View is deliberately restored to its existing legacy/model Unit source for this phase and its visible behavior is otherwise unchanged.
    Risk areas: New Edit staged data/rendering plus temporary New View source restoration only. No Old Edit behavior, Cards, persistence, CSV data, Waha routing, Probable, or unrelated UI is changed.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.75\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.71\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

# Final phase-boundary and data-completeness checks.
vm = view_pat.search(text)
em = edit_pat.search(text)
if not vm or not em:
    raise SystemExit('final iframe verification failed')
final_view = html.unescape(vm.group(2))
final_edit = html.unescape(em.group(2))
if new_edit_call in final_view:
    raise SystemExit('New View is still linked to New Edit before approval')
if legacy_call not in final_view:
    raise SystemExit('New View legacy/model source was not restored')
for required in [
    "addViewStatHeader(f);addViewUnit(f,'view-unit-row-first'",
    "addExpandedUnitMock(f)",
    "window.getNewEditUnitData=function(index)",
    "window.getNewEditHeaderData=function(){return newEditHeaderData};",
    "refreshAlternateViewUnitsFromParent();",
]:
    if required not in final_edit:
        raise SystemExit('final New Edit data check failed: ' + required)
for forbidden in ["n.textContent='Winning ORKS'", "d.textContent='Bully Boyz - Da Big Hunt - Wreckas'", "a.textContent='Priority Assets'", "z.textContent='- 1995 pts - 10 VPs'"]:
    if forbidden in final_edit:
        raise SystemExit('static New Edit header value remains: ' + forbidden)
for required in [
    '<title>WH40k 11th V31.76</title>',
    'const APP_VERSION = "31.76";',
    "version: 'V31.76',",
    'window.getAlternateViewHeaderData = function()',
    'window.getNewEditHeaderData = function()',
    'CHANGE NOTE - WH40k_11th_V31.76',
]:
    if required not in text:
        raise SystemExit('acceptance check failed: ' + required)

out.write_text(text, encoding='utf-8')
print('Built V31.76: complete New Edit data staged from Old Edit/model; New View intentionally unlinked')
