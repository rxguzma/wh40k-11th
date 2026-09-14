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


once('<title>WH40k 11th V31.110</title>', '<title>WH40k 11th V31.111</title>', 'title')
once('The current baseline is WH40k_11th_V31.110;', 'The current baseline is WH40k_11th_V31.111;', 'baseline')
once('const APP_VERSION = "31.110";', 'const APP_VERSION = "31.111";', 'APP_VERSION')
once("version: 'V31.110',", "version: 'V31.111',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing')
view_np = html.unescape(vm.group(2))

for required in [
    '.new-view-lock-toggle{grid-column:11;grid-row:4;',
    '.view-filter-toggle{grid-column:13/span 3;grid-row:4;',
    '.grid-toggle{grid-column:16;grid-row:4;',
    '.grid-toggle svg{width:16px;height:16px;',
    "toggle.className='button-standard active-green';",
    "function handleLockedViewPreparedClick(event)",
    "document.addEventListener('click',handleLockedViewPreparedClick,true);",
]:
    if required not in view_np:
        raise SystemExit('V31.111 baseline contract missing: ' + required)

style_marker = '</style>'
if view_np.count(style_marker) < 1:
    raise SystemExit('Unified New View/Edit style marker missing')
report_css = r'''
.new-view-report-toggle{grid-column:12;grid-row:4;z-index:102;align-self:center;justify-self:center;width:var(--std)!important;height:var(--std)!important;padding:0!important}
.new-view-report-toggle svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round}
.new-view-report-selected{outline:1px solid #80d6a3!important;outline-offset:-1px;color:#80d6a3!important}
'''
view_np = view_np.replace(style_marker, report_css + style_marker, 1)

helper_marker = 'function addViewHeader(f,p)'
if view_np.count(helper_marker) != 1:
    raise SystemExit(f'Report helper marker: expected 1 match, found {view_np.count(helper_marker)}')

report_helpers = r'''const NEW_VIEW_REPORT_STORAGE_KEY='wh40k:new-view-fix-reports:v1';
let newViewReportMode=false;
const newViewReportSelections=new Map();
const NEW_VIEW_STAT_FIELDS=['M','T','SV','W','LD','OC'];
const NEW_VIEW_WEAPON_FIELDS=['Range','Attacks','Skill','Strength','AP','Damage'];

function newViewReportText(el){
  return String(el&&el.textContent||'').replace(/\s+/g,' ').trim();
}
function newViewReportUnitContext(el){
  let index=null;
  const rosterNode=el&&el.closest?el.closest('[data-roster-index]'):null;
  if(rosterNode){
    const value=Number(rosterNode.dataset.rosterIndex);
    if(Number.isFinite(value))index=value;
  }
  if(index===null&&activeUnitIndex!==null)index=Number(activeUnitIndex);
  const data=index!==null&&unitDataByIndex?unitDataByIndex[index]:null;
  let name=String(data&&data.name||'').trim();
  if(!name&&rosterNode){
    const nameNode=rosterNode.querySelector('.view-unit-name');
    name=newViewReportText(nameNode);
  }
  return {index:Number.isFinite(index)?index:null,name:name||'Unit'};
}
function newViewReportWeaponIndex(el){
  const holder=el&&el.closest?el.closest('[class*="weapon-row-"],[class*="weapon-tags-"]'):null;
  if(!holder)return null;
  const match=String(holder.className||'').match(/weapon-(?:row|tags)-(\d+)/);
  return match?Number(match[1]):null;
}
function newViewReportWeaponName(el){
  const direct=el&&el.closest?el.closest('.weapon-row'):null;
  if(direct){
    const name=direct.querySelector('.weapon-name');
    if(name&&newViewReportText(name))return newViewReportText(name);
  }
  const index=newViewReportWeaponIndex(el);
  if(index!==null){
    const row=grid.querySelector('.weapon-row-'+String(index));
    const name=row&&row.querySelector('.weapon-name');
    if(name&&newViewReportText(name))return newViewReportText(name);
  }
  return 'Weapon';
}
function newViewReportClassText(el){
  return String(el&&el.className||'').toLowerCase();
}
function newViewReportGenericSection(el){
  const classes=newViewReportClassText(el);
  if(classes.includes('stratagem'))return 'Stratagem';
  if(classes.includes('enhancement'))return 'Enhancement';
  if(classes.includes('ability'))return 'Ability';
  if(classes.includes('note'))return 'Note';
  if(classes.includes('keyword'))return 'Keyword';
  return 'View';
}
function newViewReportGenericField(el){
  const classes=newViewReportClassText(el);
  if(classes.includes('description')||classes.includes('desc'))return 'Description';
  if(classes.includes('title')||classes.includes('name'))return 'Name';
  return 'Item';
}
function newViewReportGenericItem(el,section,value){
  let row=el;
  while(row&&row!==grid){
    const classes=newViewReportClassText(row);
    if(
      (section==='Ability'&&classes.includes('ability'))||
      (section==='Enhancement'&&classes.includes('enhancement'))||
      (section==='Stratagem'&&classes.includes('stratagem'))||
      (section==='Note'&&classes.includes('note'))
    )break;
    row=row.parentElement;
  }
  if(row&&row!==grid){
    const label=row.querySelector('.ability-name,.ability-title,.enhancement-name,.enhancement-title,.stratagem-name,.stratagem-title,.note-name,.note-title,[class*="-name"],[class*="-title"]');
    const labelText=newViewReportText(label);
    if(labelText)return labelText;
  }
  return value;
}
function newViewReportSelectableElement(target){
  if(!target||!target.closest)return null;
  if(target.closest('.new-view-report-toggle,.new-view-lock-toggle,.grid-toggle,.view-filter-toggle,.new-view-version-row,.new-view-version-history,.top-main-button,.detail-waha'))return null;

  const exact=target.closest(
    '.view-unit-name,.view-unit-stat,.weapon-name,.wr1,.wr2,.wr3,.wr4,.wr5,.wr6,.weapon-tag,.detail-count,.detail-core-ability'
  );
  if(exact)return exact;

  let node=target.closest('span,div');
  while(node&&node!==grid){
    const classes=newViewReportClassText(node);
    if(
      (classes.includes('ability')||
       classes.includes('enhancement')||
       classes.includes('stratagem')||
       classes.includes('note')||
       classes.includes('keyword')||
       classes.includes('description')) &&
      newViewReportText(node)
    )return node;
    node=node.parentElement;
  }
  return null;
}
function describeNewViewReportTarget(target){
  const el=newViewReportSelectableElement(target);
  if(!el)return null;
  const value=newViewReportText(el);
  if(!value)return null;

  const unit=newViewReportUnitContext(el);
  let section='View';
  let item='';
  let field='Item';

  if(el.classList.contains('view-unit-name')){
    section='Unit';item=unit.name;field='Name';
  }else if(el.classList.contains('view-unit-stat')){
    section='Stats';item='Stats';
    let statIndex=-1;
    for(let i=1;i<=6;i++)if(el.classList.contains('s'+String(i))){statIndex=i-1;break}
    field=statIndex>=0?NEW_VIEW_STAT_FIELDS[statIndex]:'Stat';
  }else if(el.classList.contains('weapon-name')){
    section='Weapon';item=value;field='Name';
  }else if([...el.classList].some(name=>/^wr[1-6]$/.test(name))){
    section='Weapon';item=newViewReportWeaponName(el);
    let statIndex=-1;
    for(let i=1;i<=6;i++)if(el.classList.contains('wr'+String(i))){statIndex=i-1;break}
    field=statIndex>=0?NEW_VIEW_WEAPON_FIELDS[statIndex]:'Field';
  }else if(el.classList.contains('weapon-tag')){
    section='Weapon';item=newViewReportWeaponName(el);field='Tag';
  }else if(el.classList.contains('detail-count')){
    section='Unit';item=unit.name;field='Count';
  }else if(el.classList.contains('detail-core-ability')){
    section='Ability';item=value;field='Name';
  }else{
    section=newViewReportGenericSection(el);
    field=newViewReportGenericField(el);
    item=newViewReportGenericItem(el,section,value);
  }

  const record={
    unitIndex:unit.index,
    unit:unit.name,
    section,
    item:item||value,
    field,
    value
  };
  record.key=[record.unitIndex??'',record.unit,record.section,record.item,record.field,record.value].join('\u001f');
  return {el,record};
}
function readNewViewFixReports(){
  try{
    const raw=localStorage.getItem(NEW_VIEW_REPORT_STORAGE_KEY);
    const parsed=raw?JSON.parse(raw):[];
    return Array.isArray(parsed)?parsed:[];
  }catch(_){return []}
}
function writeNewViewFixReports(reports){
  try{
    localStorage.setItem(NEW_VIEW_REPORT_STORAGE_KEY,JSON.stringify(reports));
    return true;
  }catch(_){return false}
}
function formatNewViewFixReportItem(item){
  const parts=[String(item.unit||'Unit'),String(item.section||'View')];
  if(item.item&&item.item!==item.unit&&item.item!==item.field)parts.push(String(item.item));
  if(item.field)parts.push(String(item.field));
  if(item.value&&item.value!==item.item)parts.push(String(item.value));
  return parts.join(' > ');
}
function saveNewViewFixReport(){
  const items=[...newViewReportSelections.values()].map(item=>Object.assign({},item));
  if(!items.length)return null;
  const rosterNode=grid.querySelector('.top-roster-name');
  const roster=newViewReportText(rosterNode)||'Roster';
  const createdAt=new Date().toISOString();
  const report={
    id:String(Date.now()),
    type:'fix-report',
    title:'FIX REPORT',
    roster,
    createdAt,
    items,
    body:items.map(formatNewViewFixReportItem).join('\n')
  };
  const reports=readNewViewFixReports();
  reports.unshift(report);
  writeNewViewFixReports(reports.slice(0,50));
  window.newViewLastFixReport=report;
  return report;
}
function syncNewViewReportButtons(){
  grid.querySelectorAll('.new-view-report-toggle').forEach(button=>{
    button.classList.toggle('active-green',newViewReportMode);
    button.setAttribute('aria-pressed',newViewReportMode?'true':'false');
    button.setAttribute('aria-label',newViewReportMode?'Save report':'Report');
    button.setAttribute('title',newViewReportMode?'Save report':'Report');
  });
}
function refreshNewViewReportMarks(){
  grid.querySelectorAll('.new-view-report-selected').forEach(el=>el.classList.remove('new-view-report-selected'));
  if(!newViewReportMode||!newViewReportSelections.size)return;
  const selector=[
    '.view-unit-name','.view-unit-stat','.weapon-name',
    '.wr1','.wr2','.wr3','.wr4','.wr5','.wr6','.weapon-tag',
    '.detail-count','.detail-core-ability',
    '[class*="ability"]','[class*="enhancement"]','[class*="stratagem"]','[class*="note"]'
  ].join(',');
  grid.querySelectorAll(selector).forEach(el=>{
    const described=describeNewViewReportTarget(el);
    if(described&&newViewReportSelections.has(described.record.key))described.el.classList.add('new-view-report-selected');
  });
}
function toggleNewViewReportMode(){
  if(newViewReportMode){
    saveNewViewFixReport();
    newViewReportMode=false;
    newViewReportSelections.clear();
    refreshNewViewReportMarks();
    syncNewViewReportButtons();
    return false;
  }
  newViewReportMode=true;
  newViewReportSelections.clear();
  syncNewViewReportButtons();
  requestAnimationFrame(refreshNewViewReportMarks);
  return true;
}
function addNewViewReportButton(f){
  const button=document.createElement('button');
  button.type='button';
  button.className='button-standard new-view-report-toggle';
  button.innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M14.7 6.3a4 4 0 0 0-5.2-5.2l2.2 2.2-2.8 2.8-2.2-2.2a4 4 0 0 0 5.2 5.2L4.3 16.7a2.1 2.1 0 0 0 3 3l7.6-7.6a4 4 0 0 0 5.2-5.2l-2.2 2.2-2.8-2.8 2.2-2.2Z"></path></svg>';
  button.onclick=event=>{event.stopPropagation();toggleNewViewReportMode()};
  f.appendChild(button);
  syncNewViewReportButtons();
  if(newViewReportMode)requestAnimationFrame(refreshNewViewReportMarks);
}
function handleNewViewReportSelection(event){
  if(!newViewReportMode||activePageMode!=='view')return;
  const target=event.target&&event.target.closest?event.target:null;
  if(!target||target.closest('.new-view-report-toggle'))return;
  const described=describeNewViewReportTarget(target);
  if(!described){
    requestAnimationFrame(refreshNewViewReportMarks);
    return;
  }
  event.preventDefault();
  event.stopImmediatePropagation();
  const key=described.record.key;
  if(newViewReportSelections.has(key)){
    newViewReportSelections.delete(key);
    described.el.classList.remove('new-view-report-selected');
  }else{
    newViewReportSelections.set(key,described.record);
    described.el.classList.add('new-view-report-selected');
  }
}
document.addEventListener('click',handleNewViewReportSelection,true);
window.getNewViewFixReports=readNewViewFixReports;
window.getNewViewLatestFixReport=function(){
  const roster=newViewReportText(grid.querySelector('.top-roster-name'));
  return readNewViewFixReports().find(report=>!roster||String(report&&report.roster||'')===roster)||null;
};

'''
view_np = view_np.replace(helper_marker, report_helpers + helper_marker, 1)

view_branch = "if(p==='view'){\n    addViewHeader(f,p);"
if view_np.count(view_branch) != 1:
    raise SystemExit(f'VIEW render branch: expected 1 match, found {view_np.count(view_branch)}')
view_np = view_np.replace(
    view_branch,
    "if(p==='view'){\n    addViewHeader(f,p);\n    addNewViewReportButton(f);",
    1,
)

locked_anchor = r'''  const filter=target.closest('.view-filter-toggle');
  if(filter){'''
locked_insert = r'''  const reportToggle=target.closest('.new-view-report-toggle');
  if(reportToggle){
    event.preventDefault();event.stopImmediatePropagation();
    toggleNewViewReportMode();
    return;
  }
  if(newViewReportMode&&describeNewViewReportTarget(target)){
    return;
  }
  const filter=target.closest('.view-filter-toggle');
  if(filter){'''
if view_np.count(locked_anchor) != 1:
    raise SystemExit(f'Locked report insertion anchor: expected 1 match, found {view_np.count(locked_anchor)}')
view_np = view_np.replace(locked_anchor, locked_insert, 1)

locked_filter_tail = r'''    showLockedViewPreparedState(activeUnitIndex,next);
    return;
  }
  const unit=target.closest('.view-unit-row[data-roster-index]');'''
locked_filter_new = r'''    showLockedViewPreparedState(activeUnitIndex,next);
    if(newViewReportMode)requestAnimationFrame(refreshNewViewReportMarks);
    return;
  }
  const unit=target.closest('.view-unit-row[data-roster-index]');'''
if view_np.count(locked_filter_tail) != 1:
    raise SystemExit(f'Locked filter report repaint: expected 1 match, found {view_np.count(locked_filter_tail)}')
view_np = view_np.replace(locked_filter_tail, locked_filter_new, 1)

locked_unit_tail = r'''    showLockedViewPreparedState(next,weaponFilterMode);
    return;
  }
  // Everything else in locked VIEW is inert'''
locked_unit_new = r'''    showLockedViewPreparedState(next,weaponFilterMode);
    if(newViewReportMode)requestAnimationFrame(refreshNewViewReportMarks);
    return;
  }
  // Everything else in locked VIEW is inert'''
if view_np.count(locked_unit_tail) != 1:
    raise SystemExit(f'Locked Unit report repaint: expected 1 match, found {view_np.count(locked_unit_tail)}')
view_np = view_np.replace(locked_unit_tail, locked_unit_new, 1)

text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.111
    Scope: Add the tabletop FIX/report wrench at L4 in unified New View using the existing 16-column grid, standard button geometry, Roboto typography, current icon stroke treatment, and existing green active color. First tap enters selection mode; individual Unit names, profile Stats, Weapon names/characteristics/Tags, core Abilities, and other Ability/Enhancement/Stratagem/Note-like displayed items can be marked without running their normal click action. Each mark stores structured context (Unit, section, item, field, current value), including individual profile Stats and Weapon characteristics. Second wrench tap saves one note-style FIX REPORT to localStorage and exits selection mode. The report engine uses one delegated click handler and the already-rendered New View cache/DOM only. Locked View explicitly permits the wrench and item marking while retaining prepared display-only Unit/filter switching and without parent/model refresh or Probable work.
    Risk areas: Unified New View L4 control, lightweight click interception while report mode is active, local FIX-report persistence, and the locked-view exception for this UI-only report interaction. Existing K4 Lock, M:O filter, P4 Grid Mode, Version/Update/Download strip, roster/model data, unified Edit, Old Edit, Cards, CSV data, Waha routing, and Probable remain unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.110\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

notes = list(re.finditer(r'\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n', text, re.S))
for match in reversed(notes[5:]):
    text = text[:match.start()] + text[match.end():]

vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing after writeback')
final_view = html.unescape(vm.group(2))

for required in [
    '.new-view-lock-toggle{grid-column:11;grid-row:4;',
    '.new-view-report-toggle{grid-column:12;grid-row:4;',
    '.view-filter-toggle{grid-column:13/span 3;grid-row:4;',
    '.grid-toggle{grid-column:16;grid-row:4;',
    '.new-view-report-toggle svg{width:16px;height:16px;',
    '.new-view-report-selected{outline:1px solid #80d6a3!important;',
    "const NEW_VIEW_REPORT_STORAGE_KEY='wh40k:new-view-fix-reports:v1';",
    'function describeNewViewReportTarget(target)',
    "const NEW_VIEW_STAT_FIELDS=['M','T','SV','W','LD','OC'];",
    "const NEW_VIEW_WEAPON_FIELDS=['Range','Attacks','Skill','Strength','AP','Damage'];",
    "section='Stats';item='Stats';",
    "section='Weapon';item=newViewReportWeaponName(el);",
    "title:'FIX REPORT',",
    "body:items.map(formatNewViewFixReportItem).join('\\n')",
    "button.className='button-standard new-view-report-toggle';",
    'addNewViewReportButton(f);',
    "document.addEventListener('click',handleNewViewReportSelection,true);",
    'window.getNewViewFixReports=readNewViewFixReports;',
    'window.getNewViewLatestFixReport=function()',
    "const reportToggle=target.closest('.new-view-report-toggle');",
    'if(newViewReportMode&&describeNewViewReportTarget(target)){',
    'if(newViewReportMode)requestAnimationFrame(refreshNewViewReportMarks);',
    'function ensurePersistentGridCells()',
    'function clearModeContent()',
]:
    if required not in final_view:
        raise SystemExit('V31.111 report acceptance failed: ' + required)

for required in [
    '<title>WH40k 11th V31.111</title>',
    'The current baseline is WH40k_11th_V31.111;',
    'const APP_VERSION = "31.111";',
    "version: 'V31.111',",
    'CHANGE NOTE - WH40k_11th_V31.111',
]:
    if required not in text:
        raise SystemExit('V31.111 outer acceptance failed: ' + required)

for forbidden in ['id="newEditPageScreen"', 'id="npEditFrame"', 'parent.getNewEdit']:
    if forbidden in text:
        raise SystemExit('V31.111 regressed retired standalone New Edit: ' + forbidden)

path.write_text(text, encoding='utf-8')
print('Built V31.111: L4 tabletop FIX/report wrench with structured item selection')
