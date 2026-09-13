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
once('<title>WH40k 11th V31.89</title>', '<title>WH40k 11th V31.90</title>', 'title')
once('The current baseline is WH40k_11th_V31.89;', 'The current baseline is WH40k_11th_V31.90;', 'baseline')
once('const APP_VERSION = "31.89";', 'const APP_VERSION = "31.90";', 'APP_VERSION')
once("version: 'V31.89',", "version: 'V31.90',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('New View iframe missing')
view_np = html.unescape(vm.group(2))

# The VIEW/EDIT controls now switch modes inside the same New View document.
old_nav = "b.onclick=()=>{if(t==='edit'&&parent&&typeof parent.openLegacyEditFromNewView==='function')parent.openLegacyEditFromNewView();else parent.UI.selectAppMode(t)};"
new_nav = "b.onclick=()=>{if(t==='view'||t==='edit')renderPage(t);else parent.UI.selectAppMode(t)};"
if view_np.count(old_nav) != 1:
    raise SystemExit(f'New View navigation handler: expected 1 match, found {view_np.count(old_nav)}')
view_np = view_np.replace(old_nav, new_nav, 1)

# Reuse the established New Edit visual language, but only expose the four
# approved controls. Move begins in grid column M (13), followed by Copy, Dead,
# and Points in N/O/P. No control functionality is migrated in this pass.
style_marker = '</style>'
if view_np.count(style_marker) < 1:
    raise SystemExit('New View style close marker missing')
edit_css = '''
.unified-edit-unit-row .edit-unit-name{grid-column:1/span 11}
.unified-edit-action{width:calc(var(--cell) - var(--gap));height:var(--std);align-self:center;justify-self:center;padding:0;border:1px solid var(--btnborder);border-radius:var(--radius);background:var(--btn);color:var(--text);font:900 var(--body)/1 Roboto,Arial,sans-serif;display:flex;align-items:center;justify-content:center}
.unified-edit-action svg{width:14px;height:14px;fill:none;stroke:currentColor;stroke-width:1.4}
.unified-edit-points{font-size:11px}
'''
view_np = view_np.replace(style_marker, edit_css + style_marker, 1)

render_marker = 'function renderPage(p){'
if view_np.count(render_marker) != 1:
    raise SystemExit(f'New View render marker: expected 1 match, found {view_np.count(render_marker)}')

edit_helpers = r'''function addUnifiedEditUnit(f,data,rowIndex){
  const r=document.createElement('div');
  r.className='edit-unit-row dynamic-roster-row unified-edit-unit-row';
  r.dataset.rosterIndex=String(rowIndex);
  const n=document.createElement('div');
  n.className='edit-unit-name';
  n.textContent=String(data&&data.name||'');
  r.appendChild(n);

  const move=document.createElement('button');
  move.type='button';move.className='unified-edit-action unified-edit-move';move.style.gridColumn='13';move.textContent='≡';move.setAttribute('aria-label','Move');
  r.appendChild(move);

  const copy=document.createElement('button');
  copy.type='button';copy.className='unified-edit-action unified-edit-copy';copy.style.gridColumn='14';copy.setAttribute('aria-label','Copy');
  copy.innerHTML='<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="5" y="5" width="9" height="9" rx="1"></rect><rect x="2" y="2" width="9" height="9" rx="1"></rect></svg>';
  r.appendChild(copy);

  const dead=document.createElement('button');
  dead.type='button';dead.className='unified-edit-action unified-edit-dead';dead.style.gridColumn='15';dead.textContent='D';dead.setAttribute('aria-label','Dead');
  r.appendChild(dead);

  const points=document.createElement('button');
  points.type='button';points.className='unified-edit-action unified-edit-points';points.style.gridColumn='16';points.setAttribute('aria-label','Points');
  const pointValue=data&&(data.points??data.pts??data.totalPoints??data.unitPoints);
  points.textContent=pointValue===undefined||pointValue===null||pointValue===''?'P':String(pointValue);
  r.appendChild(points);

  f.appendChild(r);
  return r;
}

function refreshUnifiedEditRows(){
  let rows=[];
  try{rows=parent&&typeof parent.getAlternateViewRosterRows==='function'?parent.getAlternateViewRosterRows():[]}catch(_){rows=[]}
  rows=Array.isArray(rows)?rows:[];
  grid.querySelectorAll('.dynamic-roster-row').forEach(el=>el.remove());
  let cursor=typeof FIRST_UNIT_ROW==='number'?FIRST_UNIT_ROW:7;
  rows.forEach((data,rowIndex)=>{
    if(data&&data.kind==='spacer'){
      const spacer=document.createElement('div');
      spacer.className='roster-spacer-row dynamic-roster-row';
      spacer.dataset.rosterIndex=String(rowIndex);
      spacer.style.gridRow=String(cursor++);
      grid.appendChild(spacer);
      return;
    }
    if(!data||data.kind!=='unit')return;
    const f=document.createDocumentFragment();
    const row=addUnifiedEditUnit(f,data,rowIndex);
    row.style.gridRow=String(cursor++);
    grid.appendChild(f);
  });
  const mainButton=grid.querySelector('.top-main-button');
  if(mainButton)mainButton.style.gridRow=String(cursor+1);
  return rows.some(row=>row&&row.kind==='unit');
}
window.refreshUnifiedEditRows=refreshUnifiedEditRows;

'''
view_np = view_np.replace(render_marker, edit_helpers + render_marker, 1)

# Edit mode keeps the same title/header shell, removes the View filter control,
# and intentionally does not create the Stats header or expanded Weapon detail.
old_edit_branch = "if(p==='edit'){addViewHeader(f);const viewOnly=f.querySelector('.view-filter-toggle');if(viewOnly)viewOnly.remove()}"
new_edit_branch = "if(p==='edit'){addViewHeader(f);const viewOnly=f.querySelector('.view-filter-toggle');if(viewOnly)viewOnly.remove()}"
if view_np.count(old_edit_branch) != 1:
    raise SystemExit(f'New View Edit branch: expected 1 match, found {view_np.count(old_edit_branch)}')
# Branch remains visually header-only; live Edit rows are added after append.

old_post = "if(p==='view'){requestAnimationFrame(refreshNewViewTitleFromLegacy);requestAnimationFrame(refreshAlternateViewUnitsFromParent)}"
new_post = "if(p==='view'){requestAnimationFrame(refreshNewViewTitleFromLegacy);requestAnimationFrame(refreshAlternateViewUnitsFromParent)}if(p==='edit'){requestAnimationFrame(refreshNewViewTitleFromLegacy);requestAnimationFrame(refreshUnifiedEditRows)}"
if view_np.count(old_post) != 1:
    raise SystemExit(f'New View post-render refresh: expected 1 match, found {view_np.count(old_post)}')
view_np = view_np.replace(old_post, new_post, 1)

# Write the modified New View document back. New Edit remains untouched.
view_srcdoc = html.escape(view_np, quote=True)
text = text[:vm.start(2)] + view_srcdoc + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.90
    Scope: Begin the one-page View/Edit migration inside New View. VIEW and EDIT now switch locally within the same New View iframe instead of EDIT opening Old Edit. In the New View EDIT state, Range/Melee/Other/All, the Stats header, Unit profile stats, expanded details, and Weapons are not rendered. Each live Unit row shows only Move, Copy, Dead, and Points controls using the established New Edit button styling, placed in columns M, N, O, and P respectively. Move uses the existing menu/move glyph, Copy uses the existing copy glyph, Dead uses D, and Points displays the available Unit point value when present or P otherwise. These controls are presentation-only in this pass; no edit actions are migrated yet. VIEW behavior and direct Old Edit/model data sourcing remain unchanged.
    Risk areas: New View local VIEW/EDIT switching and EDIT-state Unit-row presentation only. New Edit, Old Edit behavior, Cards, persistence, CSV data, Waha routing, Probable, and New View VIEW-mode Unit/Weapon behavior remain unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.89\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

# Retain only the five newest V31 detailed notes.
notes = list(re.finditer(r'\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n', text, re.S))
for match in reversed(notes[5:]):
    text = text[:match.start()] + text[match.end():]

# Final acceptance checks against decoded New View.
vm = view_pat.search(text)
if not vm:
    raise SystemExit('New View iframe missing after writeback')
final_view = html.unescape(vm.group(2))
required_view = [
    "if(t==='view'||t==='edit')renderPage(t)",
    'function refreshUnifiedEditRows()',
    "move.style.gridColumn='13'",
    "copy.style.gridColumn='14'",
    "dead.style.gridColumn='15'",
    "points.style.gridColumn='16'",
    "move.setAttribute('aria-label','Move')",
    "copy.setAttribute('aria-label','Copy')",
    "dead.setAttribute('aria-label','Dead')",
    "points.setAttribute('aria-label','Points')",
    "if(p==='edit'){requestAnimationFrame(refreshNewViewTitleFromLegacy);requestAnimationFrame(refreshUnifiedEditRows)}",
]
for value in required_view:
    if value not in final_view:
        raise SystemExit('V31.90 New View acceptance failed: ' + value)

# EDIT must no longer leave the page for Old Edit.
if "parent.openLegacyEditFromNewView" in final_view:
    raise SystemExit('New View EDIT still routes to Old Edit')

required_outer = [
    '<title>WH40k 11th V31.90</title>',
    'const APP_VERSION = "31.90";',
    "version: 'V31.90',",
    'CHANGE NOTE - WH40k_11th_V31.90',
]
for value in required_outer:
    if value not in text:
        raise SystemExit('V31.90 acceptance failed: ' + value)

path.write_text(text, encoding='utf-8')
print('Built V31.90: New View local Edit mode with Move/Copy/Dead/Points in M-P')
