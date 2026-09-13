from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.84.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


once('<title>WH40k 11th V31.84</title>', '<title>WH40k 11th V31.85</title>', 'title')
once('The current baseline is WH40k_11th_V31.84;', 'The current baseline is WH40k_11th_V31.85;', 'baseline')
once('const APP_VERSION = "31.84";', 'const APP_VERSION = "31.85";', 'APP_VERSION')
once("version: 'V31.84',", "version: 'V31.85',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
edit_pat = re.compile(r'(<iframe id="npEditFrame" class="np-view-frame" title="New Edit" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
em = edit_pat.search(text)
if not vm or not em:
    raise SystemExit('New View/New Edit iframe missing')
view_np = html.unescape(vm.group(2))
edit_np = html.unescape(em.group(2))

# Restore New Edit's collapsed Unit presentation to the approved old-Edit/Np1.37
# icon row. Stats remain in New Edit's local Unit record but are no longer the
# always-visible Unit list presentation.
old_branch = "if(p==='edit'){addViewHeader(f);const viewOnly=f.querySelector('.view-filter-toggle');if(viewOnly)viewOnly.remove();addViewStatHeader(f);addViewUnit(f,'view-unit-row-first','','',['','','','','','']);addViewUnit(f,'view-unit-row-second','','',['','','','','','']);addExpandedUnitMock(f)}"
new_branch = "if(p==='edit'){addViewHeader(f);const viewOnly=f.querySelector('.view-filter-toggle');if(viewOnly)viewOnly.remove();addEditUnit(f,'edit-unit-row-first','','','',0);addEditUnit(f,'edit-unit-row-second','','','',1);if(newEditOpenUnitIndex!==null)addNewEditStatsField(f,newEditOpenUnitIndex)}"
if edit_np.count(old_branch) != 1:
    raise SystemExit(f'New Edit render branch: expected 1 match, found {edit_np.count(old_branch)}')
edit_np = edit_np.replace(old_branch, new_branch, 1)

old_add_edit = "function addEditUnit(f,rowClass,name,count,pts){const r=document.createElement('div');r.className='edit-unit-row '+rowClass;addNameAndCount(r,name,count,'edit-unit-name');const menu=document.createElement('button');menu.type='button';menu.className='edit-action a1';menu.textContent='≡';r.appendChild(menu);const cp=document.createElement('button');cp.type='button';cp.className='edit-action edit-action-copy a2';cp.setAttribute('aria-label','Copy');cp.innerHTML='<svg viewBox=\"0 0 16 16\" aria-hidden=\"true\"><rect x=\"5\" y=\"5\" width=\"9\" height=\"9\" rx=\"1\"></rect><rect x=\"2\" y=\"2\" width=\"9\" height=\"9\" rx=\"1\"></rect></svg>';r.appendChild(cp);[['0','a3'],['E','a4'],['R','a5'],['D','a6']].forEach(([l,c])=>{const b=document.createElement('button');b.type='button';b.className='edit-action '+c;b.textContent=l;r.appendChild(b)});const p=document.createElement('div');p.className='edit-unit-points';p.textContent=pts;r.appendChild(p);f.appendChild(r)}"
new_add_edit = "function addEditUnit(f,rowClass,name,count,pts,index){const r=document.createElement('div');r.className='edit-unit-row '+rowClass;r.dataset.unitIndex=String(index);addNameAndCount(r,name,count,'edit-unit-name');const menu=document.createElement('button');menu.type='button';menu.className='edit-action a1';menu.textContent='≡';r.appendChild(menu);const cp=document.createElement('button');cp.type='button';cp.className='edit-action edit-action-copy a2';cp.setAttribute('aria-label','Copy');cp.innerHTML='<svg viewBox=\"0 0 16 16\" aria-hidden=\"true\"><rect x=\"5\" y=\"5\" width=\"9\" height=\"9\" rx=\"1\"></rect><rect x=\"2\" y=\"2\" width=\"9\" height=\"9\" rx=\"1\"></rect></svg>';r.appendChild(cp);[['0','a3'],['E','a4'],['R','a5'],['D','a6']].forEach(([l,c])=>{const b=document.createElement('button');b.type='button';b.className='edit-action '+c;b.textContent=l;r.appendChild(b)});const p=document.createElement('div');p.className='edit-unit-points';p.textContent=pts;r.appendChild(p);r.onclick=e=>{if(e.target.closest('button'))return;newEditOpenUnitIndex=newEditOpenUnitIndex===index?null:index;renderPage('edit')};f.appendChild(r)}"
if edit_np.count(old_add_edit) != 1:
    raise SystemExit(f'New Edit icon-row builder: expected 1 match, found {edit_np.count(old_add_edit)}')
edit_np = edit_np.replace(old_add_edit, new_add_edit, 1)

css_anchor = ".edit-action-copy svg{width:14px;height:14px;stroke:currentColor;fill:none;stroke-width:2}.edit-unit-points{grid-column:16;justify-self:center;color:var(--text);font:700 var(--body)/1 Roboto,Arial,sans-serif}"
css_add = css_anchor + ".new-edit-stats-field{grid-column:1/span 16;z-index:3;display:grid;grid-template-columns:repeat(16,var(--cell));height:var(--cell);align-items:center;background:var(--card);border-top:1px solid var(--border);border-bottom:1px solid var(--border)}.new-edit-stats-title{grid-column:1/span 4;height:var(--cell);padding-left:8px;display:flex;align-items:center;color:var(--text);font:900 var(--body)/1 Roboto,Arial,sans-serif}.new-edit-stat{height:var(--cell);display:flex;align-items:center;justify-content:center;border-left:1px solid var(--border);color:var(--text);font:700 var(--meta)/1 Roboto,Arial,sans-serif;white-space:nowrap}"
if edit_np.count(css_anchor) != 1:
    raise SystemExit(f'New Edit Stats CSS anchor: expected 1 match, found {edit_np.count(css_anchor)}')
edit_np = edit_np.replace(css_anchor, css_add, 1)

unit_marker = "let unitDataByIndex=[null,null];"
unit_add = unit_marker + "\nlet newEditOpenUnitIndex=null;"
if edit_np.count(unit_marker) != 1:
    raise SystemExit(f'New Edit Unit cache marker: expected 1 match, found {edit_np.count(unit_marker)}')
edit_np = edit_np.replace(unit_marker, unit_add, 1)

helper_marker = "function addExpandedUnitMock(f){"
helpers = r'''function addNewEditStatsField(f,index){
  const field=document.createElement('div');field.className='new-edit-stats-field';field.dataset.unitIndex=String(index);
  const title=document.createElement('div');title.className='new-edit-stats-title';title.textContent='Stats';field.appendChild(title);
  ['M"','T','SV','W','LD','OC'].forEach((label,i)=>{const cell=document.createElement('div');cell.className='new-edit-stat';cell.dataset.statIndex=String(i);cell.style.gridColumn=String(5+(i*2))+'/span 2';cell.textContent=label;field.appendChild(cell)});
  f.appendChild(field);
}
function refreshNewEditStatsField(){
  const field=grid.querySelector('.new-edit-stats-field');
  if(!field)return;
  const data=newEditOpenUnitIndex===null?null:unitDataByIndex[newEditOpenUnitIndex];
  const values=data?[data.m,data.t,data.sv,data.w,data.ld,data.oc]:[];
  const labels=['M"','T','SV','W','LD','OC'];
  field.style.display=data?'grid':'none';
  field.querySelectorAll('.new-edit-stat').forEach((cell,i)=>{cell.textContent=labels[i]+' '+String(values[i]??'')});
}

'''
if edit_np.count(helper_marker) != 1:
    raise SystemExit(f'New Edit Stats helper insertion marker: expected 1 match, found {edit_np.count(helper_marker)}')
edit_np = edit_np.replace(helper_marker, helpers + helper_marker, 1)

old_refresh = r'''function refreshNewEditUnitsFromLegacy(){
  const ok=refreshAlternateViewUnitsFromParent();
  refreshNewEditHeaderFromLegacy();
  return ok;
}'''
new_refresh = r'''function refreshNewEditUnitsFromLegacy(){
  const start=typeof FIRST_UNIT_ROW==='number'?FIRST_UNIT_ROW:7;
  let cursor=start;
  let ok=false;
  for(let index=0;index<2;index++){
    const row=grid.querySelector(index===0?'.edit-unit-row-first':'.edit-unit-row-second');
    let data=null;
    try{data=parent&&typeof parent.getAlternateViewUnitData==='function'?parent.getAlternateViewUnitData(index):null}catch(_){data=null}
    unitDataByIndex[index]=data;
    if(!row)continue;
    if(!data){row.style.display='none';if(newEditOpenUnitIndex===index)newEditOpenUnitIndex=null;continue}
    ok=true;
    row.style.display='grid';
    row.style.gridRow=String(cursor++);
    const name=row.querySelector('.edit-unit-name');
    if(name)name.textContent=String(data.name||'');
    if(newEditOpenUnitIndex===index){
      const stats=grid.querySelector('.new-edit-stats-field');
      if(stats){stats.style.gridRow=String(cursor++);stats.dataset.unitIndex=String(index)}
    }
  }
  refreshNewEditStatsField();
  refreshNewEditHeaderFromLegacy();
  return ok;
}'''
if edit_np.count(old_refresh) != 1:
    raise SystemExit(f'New Edit cache refresh bridge: expected 1 match, found {edit_np.count(old_refresh)}')
edit_np = edit_np.replace(old_refresh, new_refresh, 1)

# Write New Edit back without changing New View. New View must continue reading
# the same complete Unit record through New Edit's getNewEditUnitData bridge.
text = text[:em.start(2)] + html.escape(edit_np, quote=True) + text[em.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.85
    Scope: Return New Edit's collapsed Unit list to the old Edit/Np1.37-style icon rows instead of showing profile Stats immediately. Tapping a New Edit Unit now toggles one compact Stats field for that Unit, showing M, T, SV, W, LD, and OC. The New Edit local unitDataByIndex cache is now refreshed independently of the visible row type, so New View continues to receive the same complete Unit records and profile Stats through getNewEditUnitData(). No New View data contract, CSV data, Old Edit behavior, Weapons, Waha routing, Cards, persistence, or Probable behavior changes.
    Risk areas: New Edit Unit list presentation, Unit toggle, Stats-field presentation, and New Edit cache refresh only.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.84\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.80\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

vm = view_pat.search(text)
em = edit_pat.search(text)
if not vm or not em:
    raise SystemExit('final iframe verification failed')
final_view = html.unescape(vm.group(2))
final_edit = html.unescape(em.group(2))

for required in [
    "addEditUnit(f,'edit-unit-row-first','','','',0)",
    "addEditUnit(f,'edit-unit-row-second','','','',1)",
    "if(newEditOpenUnitIndex!==null)addNewEditStatsField(f,newEditOpenUnitIndex)",
    "let newEditOpenUnitIndex=null;",
    "title.textContent='Stats'",
    "data?[data.m,data.t,data.sv,data.w,data.ld,data.oc]:[]",
    "unitDataByIndex[index]=data;",
    "window.getNewEditUnitData=function(index)",
]:
    if required not in final_edit:
        raise SystemExit('New Edit acceptance failed: ' + required)

for forbidden in [
    "if(p==='edit'){addViewHeader(f);const viewOnly=f.querySelector('.view-filter-toggle');if(viewOnly)viewOnly.remove();addViewStatHeader(f);",
    "const ok=refreshAlternateViewUnitsFromParent();\n  refreshNewEditHeaderFromLegacy();",
]:
    if forbidden in final_edit:
        raise SystemExit('New Edit old Stats-first behavior remains: ' + forbidden)

if 'parent.getNewEditUnitData(index)' not in final_view:
    raise SystemExit('New View Unit source changed unexpectedly')
if 'parent.getAlternateViewUnitData(index)' in final_view:
    raise SystemExit('New View bypasses New Edit unexpectedly')

for required in [
    '<title>WH40k 11th V31.85</title>',
    'const APP_VERSION = "31.85";',
    "version: 'V31.85',",
    'CHANGE NOTE - WH40k_11th_V31.85',
]:
    if required not in text:
        raise SystemExit('version acceptance check failed: ' + required)

out.write_text(text, encoding='utf-8')
print('Built V31.85: New Edit icon rows with toggled Stats field; New View data cache preserved')
