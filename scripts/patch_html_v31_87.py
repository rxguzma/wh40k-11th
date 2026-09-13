from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.86.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


once('<title>WH40k 11th V31.86</title>', '<title>WH40k 11th V31.87</title>', 'title')
once('The current baseline is WH40k_11th_V31.86;', 'The current baseline is WH40k_11th_V31.87;', 'baseline')
once('const APP_VERSION = "31.86";', 'const APP_VERSION = "31.87";', 'APP_VERSION')
once("version: 'V31.86',", "version: 'V31.87',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
edit_pat = re.compile(r'(<iframe id="npEditFrame" class="np-view-frame" title="New Edit" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
em = edit_pat.search(text)
if not vm or not em:
    raise SystemExit('New View/New Edit iframe missing')
view_np = html.unescape(vm.group(2))
edit_np = html.unescape(em.group(2))


def remove_fixed_unit_row_css(doc, label):
    pattern = re.compile(
        r'(\.view-unit-row,\.edit-unit-row\{[^}]*\})'
        r'\.view-unit-row-first\{[^}]*\}'
        r'\.view-unit-row-second\{[^}]*\}'
        r'\.edit-unit-row-first\{[^}]*\}'
        r'\.edit-unit-row-second\{[^}]*\}'
    )
    replacement = r"\1.roster-spacer-row{grid-column:1/span 16;z-index:3;height:var(--cell);min-height:var(--cell)}"
    doc, count = pattern.subn(replacement, doc, count=1)
    if count != 1:
        raise SystemExit(f'{label} fixed Unit-row CSS: expected 1 match, found {count}')
    return doc


view_np = remove_fixed_unit_row_css(view_np, 'New View')
edit_np = remove_fixed_unit_row_css(edit_np, 'New Edit')

# ---------------------------------------------------------------------------
# Parent/model bridge: preserve actual roster row order, including spacers.
# Existing getAlternateViewUnitData(index) remains the canonical Unit-record
# builder; this wrapper adds row type/order without duplicating that contract.
# ---------------------------------------------------------------------------
select_marker = '\n\n    function selectAppMode(mode) {'
parent_unit_start = text.find('    window.getAlternateViewUnitData = function(index) {')
if parent_unit_start < 0:
    raise SystemExit('parent Unit bridge missing')
parent_unit_end = text.find(select_marker, parent_unit_start)
if parent_unit_end < 0:
    raise SystemExit('parent Unit bridge end missing')
parent_block = text[parent_unit_start:parent_unit_end]
if 'window.getAlternateViewRosterRows' in parent_block:
    raise SystemExit('parent roster-row bridge already exists')
parent_rows = '''

    window.getAlternateViewRosterRows = function() {
      const roster = appEditMode && viewEditRosterDraft ? getViewEditRoster() : getActiveRoster();
      const models = getRosterEntryModels(roster).filter(item => item && !item.isNote && !item.isDeleted && !item.isMissingUnit);
      let unitIndex = 0;
      return models.map(item => {
        if (item.isSpacer) return { kind: "spacer" };
        const data = window.getAlternateViewUnitData(unitIndex++);
        return data ? Object.assign({ kind: "unit" }, data) : null;
      }).filter(Boolean);
    };'''
text = text[:parent_unit_end] + parent_rows + text[parent_unit_end:]

# Parent-facing New Edit bridge used by New View. New View therefore still
# receives display data only through New Edit, now as ordered roster rows.
new_edit_header_marker = '    window.getNewEditHeaderData = function() {'
bridge_pos = text.find(new_edit_header_marker)
if bridge_pos < 0:
    raise SystemExit('parent New Edit header bridge missing')
if 'window.getNewEditRosterRows = function()' in text:
    raise SystemExit('parent New Edit roster-row bridge already exists')
new_edit_rows_bridge = '''    window.getNewEditRosterRows = function() {
      const frame = document.getElementById("npEditFrame");
      try {
        const editWindow = frame && frame.contentWindow;
        if (editWindow && typeof editWindow.refreshNewEditUnitsFromLegacy === "function") editWindow.refreshNewEditUnitsFromLegacy();
        const rows = editWindow && typeof editWindow.getNewEditRosterRows === "function"
          ? editWindow.getNewEditRosterRows()
          : [];
        return Array.isArray(rows) ? rows : [];
      } catch (_) {
        return [];
      }
    };

'''
text = text[:bridge_pos] + new_edit_rows_bridge + text[bridge_pos:]

# ---------------------------------------------------------------------------
# New Edit: remove the inherited two-Unit View controller completely. New Edit
# now owns a simple dynamic roster-row cache and the approved Stats toggle.
# ---------------------------------------------------------------------------
edit_controller_start = edit_np.find('let activeUnitIndex=null;')
edit_controller_end_marker = 'window.refreshAlternateViewUnitsFromParent=refreshAlternateViewUnitsFromParent;'
edit_controller_end = edit_np.find(edit_controller_end_marker, edit_controller_start)
if edit_controller_start < 0 or edit_controller_end < 0:
    raise SystemExit('New Edit inherited controller bounds missing')
edit_controller_end += len(edit_controller_end_marker)
edit_controller = '''let weaponFilterMode='ALL';
function cycleWeaponFilter(){}
const FIRST_UNIT_ROW=7;
let newEditRosterRows=[];
let newEditOpenRowIndex=null;'''
edit_np = edit_np[:edit_controller_start] + edit_controller + edit_np[edit_controller_end:]

old_add_edit = "function addEditUnit(f,rowClass,name,count,pts,index){const r=document.createElement('div');r.className='edit-unit-row '+rowClass;r.dataset.unitIndex=String(index);addNameAndCount(r,name,count,'edit-unit-name');const menu=document.createElement('button');menu.type='button';menu.className='edit-action a1';menu.textContent='≡';r.appendChild(menu);const cp=document.createElement('button');cp.type='button';cp.className='edit-action edit-action-copy a2';cp.setAttribute('aria-label','Copy');cp.innerHTML='<svg viewBox=\"0 0 16 16\" aria-hidden=\"true\"><rect x=\"5\" y=\"5\" width=\"9\" height=\"9\" rx=\"1\"></rect><rect x=\"2\" y=\"2\" width=\"9\" height=\"9\" rx=\"1\"></rect></svg>';r.appendChild(cp);[['0','a3'],['E','a4'],['R','a5'],['D','a6']].forEach(([l,c])=>{const b=document.createElement('button');b.type='button';b.className='edit-action '+c;b.textContent=l;r.appendChild(b)});const p=document.createElement('div');p.className='edit-unit-points';p.textContent=pts;r.appendChild(p);r.onclick=e=>{if(e.target.closest('button'))return;newEditOpenUnitIndex=newEditOpenUnitIndex===index?null:index;renderPage('edit')};f.appendChild(r)}"
new_add_edit = "function addEditUnit(f,name,count,pts,rowIndex){const r=document.createElement('div');r.className='edit-unit-row dynamic-roster-row';r.dataset.rosterIndex=String(rowIndex);addNameAndCount(r,name,count,'edit-unit-name');const menu=document.createElement('button');menu.type='button';menu.className='edit-action a1';menu.textContent='≡';r.appendChild(menu);const cp=document.createElement('button');cp.type='button';cp.className='edit-action edit-action-copy a2';cp.setAttribute('aria-label','Copy');cp.innerHTML='<svg viewBox=\"0 0 16 16\" aria-hidden=\"true\"><rect x=\"5\" y=\"5\" width=\"9\" height=\"9\" rx=\"1\"></rect><rect x=\"2\" y=\"2\" width=\"9\" height=\"9\" rx=\"1\"></rect></svg>';r.appendChild(cp);[['0','a3'],['E','a4'],['R','a5'],['D','a6']].forEach(([l,c])=>{const b=document.createElement('button');b.type='button';b.className='edit-action '+c;b.textContent=l;r.appendChild(b)});const p=document.createElement('div');p.className='edit-unit-points';p.textContent=pts;r.appendChild(p);r.onclick=e=>{if(e.target.closest('button'))return;newEditOpenRowIndex=newEditOpenRowIndex===rowIndex?null:rowIndex;refreshNewEditUnitsFromLegacy()};f.appendChild(r);return r}"
if edit_np.count(old_add_edit) != 1:
    raise SystemExit(f'New Edit Unit builder: expected 1 match, found {edit_np.count(old_add_edit)}')
edit_np = edit_np.replace(old_add_edit, new_add_edit, 1)

stats_start = edit_np.find('function addNewEditStatsField(f,index){')
stats_end = edit_np.find('function addExpandedUnitMock(f){', stats_start)
if stats_start < 0 or stats_end < 0:
    raise SystemExit('New Edit Stats helper bounds missing')
new_stats = '''function addNewEditStatsField(f,rowIndex,data){
  const field=document.createElement('div');field.className='new-edit-stats-field';field.dataset.rosterIndex=String(rowIndex);
  const title=document.createElement('div');title.className='new-edit-stats-title';title.textContent='Stats';field.appendChild(title);
  const labels=['M"','T','SV','W','LD','OC'];
  const values=data?[data.m,data.t,data.sv,data.w,data.ld,data.oc]:[];
  labels.forEach((label,i)=>{const cell=document.createElement('div');cell.className='new-edit-stat';cell.dataset.statIndex=String(i);cell.style.gridColumn=String(5+(i*2))+'/span 2';cell.textContent=label+' '+String(values[i]??'');field.appendChild(cell)});
  f.appendChild(field);
  return field;
}

'''
edit_np = edit_np[:stats_start] + new_stats + edit_np[stats_end:]

refresh_start = edit_np.find('function refreshNewEditUnitsFromLegacy(){')
refresh_end = edit_np.find('window.refreshNewEditUnitsFromLegacy=refreshNewEditUnitsFromLegacy;', refresh_start)
if refresh_start < 0 or refresh_end < 0:
    raise SystemExit('New Edit refresh bounds missing')
refresh_end += len('window.refreshNewEditUnitsFromLegacy=refreshNewEditUnitsFromLegacy;')
new_edit_refresh = '''function refreshNewEditUnitsFromLegacy(){
  let rows=[];
  try{rows=parent&&typeof parent.getAlternateViewRosterRows==='function'?parent.getAlternateViewRosterRows():[]}catch(_){rows=[]}
  newEditRosterRows=Array.isArray(rows)?rows:[];
  if(newEditOpenRowIndex!==null){
    const openData=newEditRosterRows[newEditOpenRowIndex];
    if(!openData||openData.kind!=='unit')newEditOpenRowIndex=null;
  }
  grid.querySelectorAll('.dynamic-roster-row,.new-edit-stats-field').forEach(el=>el.remove());
  let cursor=FIRST_UNIT_ROW;
  let ok=false;
  newEditRosterRows.forEach((data,rowIndex)=>{
    if(data&&data.kind==='spacer'){
      const spacer=document.createElement('div');
      spacer.className='roster-spacer-row dynamic-roster-row';
      spacer.dataset.rosterIndex=String(rowIndex);
      spacer.style.gridRow=String(cursor++);
      grid.appendChild(spacer);
      return;
    }
    if(!data||data.kind!=='unit')return;
    ok=true;
    const f=document.createDocumentFragment();
    const row=addEditUnit(f,String(data.name||''),'','',rowIndex);
    row.style.gridRow=String(cursor++);
    if(newEditOpenRowIndex===rowIndex){
      const stats=addNewEditStatsField(f,rowIndex,data);
      stats.style.gridRow=String(cursor++);
    }
    grid.appendChild(f);
  });
  refreshNewEditHeaderFromLegacy();
  return ok;
}
window.getNewEditRosterRows=function(){return newEditRosterRows.slice()};
window.getNewEditUnitData=function(index){
  const clean=Math.max(0,Number(index)||0);
  const units=newEditRosterRows.filter(row=>row&&row.kind==='unit');
  return units[clean]||null;
};
window.refreshNewEditUnitsFromLegacy=refreshNewEditUnitsFromLegacy;'''
edit_np = edit_np[:refresh_start] + new_edit_refresh + edit_np[refresh_end:]

old_edit_branch = "if(p==='edit'){addViewHeader(f);const viewOnly=f.querySelector('.view-filter-toggle');if(viewOnly)viewOnly.remove();addEditUnit(f,'edit-unit-row-first','','','',0);addEditUnit(f,'edit-unit-row-second','','','',1);if(newEditOpenUnitIndex!==null)addNewEditStatsField(f,newEditOpenUnitIndex)}"
new_edit_branch = "if(p==='edit'){addViewHeader(f);const viewOnly=f.querySelector('.view-filter-toggle');if(viewOnly)viewOnly.remove()}"
if edit_np.count(old_edit_branch) != 1:
    raise SystemExit(f'New Edit render branch: expected 1 match, found {edit_np.count(old_edit_branch)}')
edit_np = edit_np.replace(old_edit_branch, new_edit_branch, 1)

# ---------------------------------------------------------------------------
# New View: retain the current detail/Weapon renderer, but make Unit rows and
# expansion placement derive from ordered roster rows rather than positions 0/1.
# ---------------------------------------------------------------------------
if view_np.count('let unitDataByIndex=[null,null];') != 1:
    raise SystemExit('New View two-slot cache marker missing')
view_np = view_np.replace('let unitDataByIndex=[null,null];', 'let unitDataByIndex=[];', 1)
if view_np.count('const SECOND_UNIT_AUTHORED_ROW=20;') != 1:
    raise SystemExit('New View second-Unit authored-row marker missing')
view_np = view_np.replace('const SECOND_UNIT_AUTHORED_ROW=20;\n', '', 1)
old_unit_row = "function unitRow(index){return grid.querySelector(index===0?'.view-unit-row-first':'.view-unit-row-second')}"
new_unit_row = "function unitRow(index){return grid.querySelector('.view-unit-row[data-roster-index=\"'+String(index)+'\"]')}"
if view_np.count(old_unit_row) != 1:
    raise SystemExit(f'New View fixed Unit selector: expected 1 match, found {view_np.count(old_unit_row)}')
view_np = view_np.replace(old_unit_row, new_unit_row, 1)

layout_start = view_np.find('function syncExpandedLayout(expansionRows){')
layout_end = view_np.find('function applyActiveUnitDetails(){', layout_start)
if layout_start < 0 or layout_end < 0:
    raise SystemExit('New View expanded-layout bounds missing')
new_layout = '''function syncExpandedLayout(expansionRows){
  const usedRows=activeUnitIndex===null?0:Math.max(0,Number(expansionRows)||0);
  let cursor=FIRST_UNIT_ROW;
  grid.querySelectorAll('.dynamic-roster-row').forEach(row=>{
    row.style.gridRow=String(cursor++);
    if(activeUnitIndex!==null&&Number(row.dataset.rosterIndex)===activeUnitIndex)cursor+=usedRows;
  });
  const mainButton=grid.querySelector('.top-main-button');
  if(mainButton)mainButton.style.gridRow=String(cursor+1);
  const activeGridRows=Math.max(cursor+2,FIRST_UNIT_ROW+unitDataByIndex.length+usedRows+2);
  grid.querySelectorAll('.grid-cell').forEach(cell=>{
    const row=parseInt(cell.style.gridRow||'',10);
    cell.hidden=Number.isFinite(row)&&row>activeGridRows;
  });
}
'''
view_np = view_np[:layout_start] + new_layout + view_np[layout_end:]

old_active_row = "const activeRow=activeUnitIndex===1?FIRST_UNIT_ROW+1:FIRST_UNIT_ROW;"
new_active_row = "const activeUnitRow=activeUnitIndex===null?null:unitRow(activeUnitIndex);\n  const activeRow=activeUnitRow?parseInt(activeUnitRow.style.gridRow||getComputedStyle(activeUnitRow).gridRowStart,10):FIRST_UNIT_ROW;"
active_row_count = view_np.count(old_active_row)
if active_row_count != 2:
    raise SystemExit(f'New View fixed active-row logic: expected 2 matches, found {active_row_count}')
view_np = view_np.replace(old_active_row, new_active_row)

old_visibility_loop = "for(let index=0;index<2;index++){\n    const row=unitRow(index);\n    if(row)row.classList.toggle('unit-active',activeUnitIndex===index);\n  }"
new_visibility_loop = "grid.querySelectorAll('.view-unit-row[data-roster-index]').forEach(row=>{\n    row.classList.toggle('unit-active',activeUnitIndex===Number(row.dataset.rosterIndex));\n  });"
if view_np.count(old_visibility_loop) != 1:
    raise SystemExit(f'New View active Unit loop: expected 1 match, found {view_np.count(old_visibility_loop)}')
view_np = view_np.replace(old_visibility_loop, new_visibility_loop, 1)

view_refresh_start = view_np.find('function refreshAlternateViewUnitsFromParent(){')
view_refresh_end = view_np.find('window.refreshAlternateViewUnitsFromParent=refreshAlternateViewUnitsFromParent;', view_refresh_start)
if view_refresh_start < 0 or view_refresh_end < 0:
    raise SystemExit('New View refresh bounds missing')
view_refresh_end += len('window.refreshAlternateViewUnitsFromParent=refreshAlternateViewUnitsFromParent;')
new_view_refresh = '''function refreshAlternateViewUnitsFromParent(){
  let rows=[];
  try{rows=parent&&typeof parent.getNewEditRosterRows==='function'?parent.getNewEditRosterRows():[]}catch(_){rows=[]}
  rows=Array.isArray(rows)?rows:[];
  unitDataByIndex=[];
  grid.querySelectorAll('.dynamic-roster-row').forEach(el=>el.remove());
  const f=document.createDocumentFragment();
  let cursor=FIRST_UNIT_ROW;
  rows.forEach((data,rowIndex)=>{
    if(data&&data.kind==='spacer'){
      const spacer=document.createElement('div');
      spacer.className='roster-spacer-row dynamic-roster-row';
      spacer.dataset.rosterIndex=String(rowIndex);
      spacer.style.gridRow=String(cursor++);
      f.appendChild(spacer);
      return;
    }
    if(!data||data.kind!=='unit')return;
    unitDataByIndex[rowIndex]=data;
    const before=f.childNodes.length;
    addViewUnit(f,'dynamic-roster-row',String(data.name||''),'',[data.m,data.t,data.sv,data.w,data.ld,data.oc]);
    const row=f.childNodes[before];
    row.dataset.rosterIndex=String(rowIndex);
    row.style.gridRow=String(cursor++);
    row.onclick=()=>toggleUnitDetails(rowIndex);
  });
  grid.appendChild(f);
  if(activeUnitIndex!==null&&!unitDataByIndex[activeUnitIndex])activeUnitIndex=null;
  selectedWeaponIndex=null;
  applyActiveUnitDetails();
  syncUnitDetailVisibility();
  return unitDataByIndex.some(Boolean);
}
window.refreshAlternateViewUnitsFromParent=refreshAlternateViewUnitsFromParent;'''
view_np = view_np[:view_refresh_start] + new_view_refresh + view_np[view_refresh_end:]

old_view_branch = "if(p==='view'){addViewHeader(f);addViewStatHeader(f);addViewUnit(f,'view-unit-row-first','','',['','','','','','']);addViewUnit(f,'view-unit-row-second','','',['','','','','','']);addExpandedUnitMock(f)}"
new_view_branch = "if(p==='view'){addViewHeader(f);addViewStatHeader(f);addExpandedUnitMock(f)}"
if view_np.count(old_view_branch) != 1:
    raise SystemExit(f'New View render branch: expected 1 match, found {view_np.count(old_view_branch)}')
view_np = view_np.replace(old_view_branch, new_view_branch, 1)

# New View must use New Edit's ordered-row contract and preserve V31.86 filter
# state. Opening/refreshing Units may clear Weapon selection, never the filter.
if 'parent.getNewEditRosterRows' not in view_np:
    raise SystemExit('New View ordered-row source missing')
if "weaponFilterMode='ALL';" not in view_np:
    raise SystemExit('New View initial ALL default missing')
toggle_match = re.search(r'function toggleUnitDetails\(index\)\{(.*?)\n\}', view_np, re.S)
refresh_match = re.search(r'function refreshAlternateViewUnitsFromParent\(\)\{(.*?)\n\}', view_np, re.S)
if not toggle_match or not refresh_match:
    raise SystemExit('New View controller verification missing')
for body, label in [(toggle_match.group(1), 'Unit toggle'), (refresh_match.group(1), 'Unit refresh')]:
    if 'weaponFilterMode=' in body:
        raise SystemExit(f'{label} regressed V31.86 filter persistence')

# Write both embedded pages back.
text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]
em = edit_pat.search(text)
if not em:
    raise SystemExit('New Edit iframe missing after New View writeback')
text = text[:em.start(2)] + html.escape(edit_np, quote=True) + text[em.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.87
    Scope: Remove the hard-coded two-Unit assumptions from New Edit and New View, then wire both pages to the actual ordered roster rows. New Edit now stages an ordered row contract that preserves blank/spacer rows and any number of Unit rows; New View consumes that ordered contract only through New Edit. Unit rows are generated dynamically, spacer rows occupy one literal blank grid row, third and later Units use the same existing New Edit icon row / Stats toggle and New View Unit/detail/Weapon behavior as earlier Units, and expanded-detail placement is derived from the active rendered row rather than first/second authored positions. V31.86 View filter persistence is preserved.
    Risk areas: New Edit/New View roster-row generation, blank-row spacing, Unit open/collapse placement, and dynamic downstream row shifting. Old Edit, Cards, persistence, CSV contents, Waha routing behavior, Probable, and unrelated UI are unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.86\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.82\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

# Final acceptance: the Unit-count/position hardcoding identified in the audit
# must be gone from the active New View/New Edit documents.
vm = view_pat.search(text)
em = edit_pat.search(text)
if not vm or not em:
    raise SystemExit('final iframe verification failed')
final_view = html.unescape(vm.group(2))
final_edit = html.unescape(em.group(2))

for doc, label in [(final_view, 'New View'), (final_edit, 'New Edit')]:
    for forbidden in [
        'index<2',
        '[null,null]',
        'SECOND_UNIT_AUTHORED_ROW',
        '.view-unit-row-first',
        '.view-unit-row-second',
        '.edit-unit-row-first',
        '.edit-unit-row-second',
        'activeUnitIndex===1?FIRST_UNIT_ROW+1:FIRST_UNIT_ROW',
    ]:
        if forbidden in doc:
            raise SystemExit(f'{label} still contains fixed two-Unit hardcoding: {forbidden}')

for required in [
    'window.getAlternateViewRosterRows = function()',
    'window.getNewEditRosterRows = function()',
    "parent.getAlternateViewRosterRows==='function'",
    "parent.getNewEditRosterRows==='function'",
    "data.kind==='spacer'",
    "data.kind==='unit'",
    "className='roster-spacer-row dynamic-roster-row'",
    '<title>WH40k 11th V31.87</title>',
    'const APP_VERSION = "31.87";',
    "version: 'V31.87',",
    'CHANGE NOTE - WH40k_11th_V31.87',
]:
    if required not in text:
        raise SystemExit('V31.87 acceptance failed: ' + required)

out.write_text(text, encoding='utf-8')
print('Built V31.87: dynamic New Edit/New View roster rows with spacers and 3rd+ Units')
