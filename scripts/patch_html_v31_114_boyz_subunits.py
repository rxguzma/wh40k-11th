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
once('<title>WH40k 11th V31.113</title>', '<title>WH40k 11th V31.114</title>', 'title')
once('The current baseline is WH40k_11th_V31.113;', 'The current baseline is WH40k_11th_V31.114;', 'baseline')
once('const APP_VERSION = "31.113";', 'const APP_VERSION = "31.114";', 'APP_VERSION')
once("version: 'V31.113',", "version: 'V31.114',", 'quality version')

# Remove the rejected V31.110 flat Boyz weapon list from unified EDIT.
for css in [
    '.unified-edit-weapon-row{grid-column:1/span 16;min-height:var(--cell);display:flex;align-items:center;padding:0 8px;overflow:hidden;color:var(--secondary);font:700 var(--body)/1 Roboto,Arial,sans-serif;white-space:nowrap}\n',
    '.unified-edit-weapon-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}\n',
    '.unified-edit-weapon-count{flex:0 0 auto;margin-left:6px;color:var(--orange);font-weight:900}\n',
]:
    text = text.replace(css, '')
text = re.sub(
    r'\nconst BOYZ_UNIFIED_EDIT_WEAPONS=.*?\nfunction renderUnifiedEditRows\(rows\)\{',
    '\nfunction renderUnifiedEditRows(rows){',
    text,
    count=1,
    flags=re.S,
)
text = text.replace('    cursor=addBoyzUnifiedEditWeaponRows(f,data,rowIndex,cursor);\n', '')

# New View needs the full Boyz weapon set plus canonical IDs/quantities. Other
# Units keep exactly the same weapon data; the normal renderer still uses five.
old_slice = '        weapons: weapons.slice(0,5).map(weapon => {'
if old_slice not in text:
    raise SystemExit('New View parent weapon slice anchor missing')
text = text.replace(old_slice, '        weapons: weapons.map(weapon => {', 1)

outer_name = '        name: String(model.displayName || (model.unit && model.unit.name) || ""),'
if text.count(outer_name) != 1:
    raise SystemExit(f'New View parent Unit name anchor: expected 1 match, found {text.count(outer_name)}')
text = text.replace(outer_name, outer_name + '\n        unitId: String(unit && unit.unitId || ""),', 1)

weapon_return = '          return {\n            name: String(weapon.name || weapon.weaponId || ""),'
if text.count(weapon_return) != 1:
    raise SystemExit(f'New View parent weapon return anchor: expected 1 match, found {text.count(weapon_return)}')
text = text.replace(
    weapon_return,
    '          return {\n            weaponId: String(weapon.weaponId || ""),\n            quantity: entry && unit ? getRosterWeaponQuantity(entry, unit, weapon) : 0,\n            name: String(weapon.name || weapon.weaponId || ""),',
    1,
)

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing')
view_np = html.unescape(vm.group(2))

# Boyz-only sub-units. They deliberately reuse the existing weapon-header,
# weapon-row, weapon-stat, weapon-tags and state classes with no new visual CSS.
marker = 'function syncWeaponLayout(){'
if view_np.count(marker) != 1:
    raise SystemExit(f'New View syncWeaponLayout marker: expected 1 match, found {view_np.count(marker)}')

helpers = r'''const BOYZ_NEW_VIEW_SUBUNITS=[
  {label:'Boyz',weaponIds:['SLUGGA','SHOOTA','CHOPPA']},
  {label:'Specials',weaponIds:['BIG_SHOOTA','BURNA','ROKKIT_LAUNCHA_BLASTA','ROKKIT_LAUNCHA_BUSTA']},
  {label:'Nob',weaponIds:['KOMBI_SKORCHA_SHOOTA','KOMBI_SKORCHA_SKORCHA']}
];
const boyzNewViewSubunitOpen={Boyz:false,Specials:false,Nob:false};
let boyzNewViewSelectedWeaponId='';
function normalizeBoyzWeaponId(value){return String(value||'').trim().toUpperCase()}
function isBoyzNewViewData(data){return normalizeBoyzWeaponId(data&&data.unitId)==='BOYZ'||String(data&&data.name||'').trim().toUpperCase()==='BOYZ'}
function clearBoyzNewViewRows(){
  grid.querySelectorAll('.boyz-subunit-node').forEach(node=>node.remove());
  const header=grid.querySelector('.weapon-header:not(.boyz-subunit-node)');
  if(header)header.style.removeProperty('display');
  for(let i=1;i<=5;i++){
    const row=grid.querySelector('.weapon-row-'+i);if(row)row.style.removeProperty('display');
    const tags=grid.querySelector('.weapon-tags-'+i);if(tags)tags.style.removeProperty('display');
  }
}
function boyzWeaponPassesFilter(weapon){
  if(weaponFilterMode==='ALL')return true;
  const scope=String(weapon&&weapon.scope||'OTHER').toUpperCase();
  return scope===weaponFilterMode;
}
function refreshBoyzNewViewSelection(){
  const selected=normalizeBoyzWeaponId(boyzNewViewSelectedWeaponId);
  grid.querySelectorAll('.boyz-subunit-weapon').forEach(row=>{
    const active=Boolean(selected)&&normalizeBoyzWeaponId(row.dataset.weaponId)===selected;
    const muted=Boolean(selected)&&!active;
    row.classList.toggle('weapon-active',active);
    row.classList.toggle('weapon-muted',muted);
    const tags=grid.querySelector('.boyz-subunit-tags[data-weapon-id="'+String(row.dataset.weaponId||'')+'"]');
    if(tags)tags.classList.toggle('weapon-muted',muted);
  });
}
function makeBoyzSubunitHeader(template,label){
  const row=template.cloneNode(true);
  row.classList.add('boyz-subunit-node','boyz-subunit-header');
  row.style.display='grid';
  const name=row.querySelector('.weapon-name');
  if(name)name.textContent=label;
  row.onclick=e=>{
    e.stopPropagation();
    boyzNewViewSubunitOpen[label]=!boyzNewViewSubunitOpen[label];
    renderBoyzNewViewSubunits(unitDataByIndex[activeUnitIndex]);
  };
  return row;
}
function makeBoyzWeaponRow(template,weapon){
  const row=template.cloneNode(true);
  row.className='weapon-row boyz-subunit-node boyz-subunit-weapon';
  row.style.display='grid';
  row.dataset.weaponId=String(weapon.weaponId||'');
  row.dataset.scope=String(weapon.scope||'OTHER');
  const qty=Math.max(0,Number(weapon.quantity)||0);
  const name=row.querySelector('.weapon-name');
  if(name)name.textContent=String(weapon.name||weapon.weaponId||'')+(qty>0?' ×'+String(qty):'');
  [weapon.range,weapon.attacks,weapon.skill,weapon.strength,weapon.ap,weapon.damage].forEach((value,index)=>{
    const cell=row.querySelector('.wr'+String(index+1));if(cell)cell.textContent=String(value??'');
  });
  row.onclick=e=>{
    e.stopPropagation();
    const id=String(row.dataset.weaponId||'');
    boyzNewViewSelectedWeaponId=normalizeBoyzWeaponId(boyzNewViewSelectedWeaponId)===normalizeBoyzWeaponId(id)?'':id;
    refreshBoyzNewViewSelection();
  };
  return row;
}
function makeBoyzWeaponTags(template,weapon){
  const tags=Array.isArray(weapon.tags)?weapon.tags:[];
  if(!tags.length)return null;
  const row=template.cloneNode(true);
  row.className='weapon-tags boyz-subunit-node boyz-subunit-tags';
  row.style.display='flex';
  row.dataset.weaponId=String(weapon.weaponId||'');
  const tagEls=[...row.querySelectorAll('.weapon-tag')];
  tagEls.forEach((el,index)=>{el.textContent=String(tags[index]||'');el.style.display=tags[index]?'inline-flex':'none'});
  return row;
}
function renderBoyzNewViewSubunits(data){
  clearBoyzNewViewRows();
  if(!isBoyzNewViewData(data)||activeUnitIndex===null)return false;
  const baseHeader=grid.querySelector('.weapon-header:not(.boyz-subunit-node)');
  const baseWeapon=grid.querySelector('.weapon-row-1');
  const baseTags=grid.querySelector('.weapon-tags-1');
  const detailRow=grid.querySelector('.detail-box-row');
  const activeRowNode=unitRow(activeUnitIndex);
  if(!baseHeader||!baseWeapon||!baseTags||!detailRow||!activeRowNode)return false;
  baseHeader.style.display='none';
  for(let i=1;i<=5;i++){
    const row=grid.querySelector('.weapon-row-'+i);if(row)row.style.display='none';
    const tags=grid.querySelector('.weapon-tags-'+i);if(tags)tags.style.display='none';
  }
  const allWeapons=Array.isArray(data.weapons)?data.weapons:[];
  const byId=new Map(allWeapons.map(weapon=>[normalizeBoyzWeaponId(weapon&&weapon.weaponId),weapon]));
  const nodes=[];
  BOYZ_NEW_VIEW_SUBUNITS.forEach(def=>{
    nodes.push(makeBoyzSubunitHeader(baseHeader,def.label));
    if(!boyzNewViewSubunitOpen[def.label])return;
    def.weaponIds.forEach(id=>{
      const weapon=byId.get(id);
      if(!weapon||!boyzWeaponPassesFilter(weapon))return;
      nodes.push(makeBoyzWeaponRow(baseWeapon,weapon));
      const tagRow=makeBoyzWeaponTags(baseTags,weapon);
      if(tagRow)nodes.push(tagRow);
    });
  });
  nodes.forEach(node=>grid.appendChild(node));
  const usedRows=1+nodes.length;
  syncExpandedLayout(usedRows);
  const finalUnit=unitRow(activeUnitIndex);
  const finalUnitRow=finalUnit?parseInt(finalUnit.style.gridRow||getComputedStyle(finalUnit).gridRowStart,10):FIRST_UNIT_ROW;
  const detailStart=(Number.isFinite(finalUnitRow)?finalUnitRow:FIRST_UNIT_ROW)+1;
  detailRow.style.gridRow=String(detailStart);
  nodes.forEach((node,index)=>{node.style.gridRow=String(detailStart+1+index)});
  refreshBoyzNewViewSelection();
  if(typeof syncNewViewFrameHeight==='function')requestAnimationFrame(syncNewViewFrameHeight);
  return true;
}
'''
view_np = view_np.replace(marker, helpers + marker, 1)

# Route only Boyz through the sub-unit renderer; all other Units retain the
# existing fixed five-row New View path unchanged.
old_sync_head = "function syncWeaponLayout(){\n  const filterButton=grid.querySelector('.view-filter-toggle');\n  if(filterButton)filterButton.textContent=weaponFilterMode;"
new_sync_head = "function syncWeaponLayout(){\n  const filterButton=grid.querySelector('.view-filter-toggle');\n  if(filterButton)filterButton.textContent=weaponFilterMode;\n  const activeData=activeUnitIndex===null?null:unitDataByIndex[activeUnitIndex];\n  if(isBoyzNewViewData(activeData)){renderBoyzNewViewSubunits(activeData);return}\n  clearBoyzNewViewRows();"
if view_np.count(old_sync_head) != 1:
    raise SystemExit(f'New View syncWeaponLayout head: expected 1 match, found {view_np.count(old_sync_head)}')
view_np = view_np.replace(old_sync_head, new_sync_head, 1)

text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.114
    Scope: Boyz New View weapon sub-units. When Boyz is expanded in VIEW, its Weapon area now shows exactly three independently tappable header rows: Boyz, Specials, and Nob. Headers reuse the existing weapon-header cells with R\" / A / WS / St / AP / D and add no arrows, counts, controls, borders, or new colors. Initial approved contents are Boyz = Slugga/Shoota/Choppa; Specials = Big Shoota/Burna/Rokkit Launcha Blasta/Rokkit Launcha Busta; Nob = Kombi-skorcha Shoota/Kombi-skorcha Skorcha. Expanded rows reuse current New View weapon/stat/tag styling. Canonical Weapon_Quantities supplies x10/x20 quantities, appended directly to the weapon-name text as ×N so active/muted/normal states apply to the whole name. The rejected V31.110 flat weapon list is removed from unified EDIT.
    Risk areas: Boyz expanded Weapon presentation in unlocked New View and removal of the rejected V31.110 Edit-only flat list. Other Units, New View filters, Unit Detail, lock/frozen behavior, unified Edit rows, FIX reports, Version controls, Cards, persistence, CSV data, Waha routing, and Probable remain unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.113\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

notes = list(re.finditer(r'\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n', text, re.S))
for match in reversed(notes[5:]):
    text = text[:match.start()] + text[match.end():]

# Acceptance checks.
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing after writeback')
final_view = html.unescape(vm.group(2))
for required in [
    "{label:'Boyz',weaponIds:['SLUGGA','SHOOTA','CHOPPA']}",
    "{label:'Specials',weaponIds:['BIG_SHOOTA','BURNA','ROKKIT_LAUNCHA_BLASTA','ROKKIT_LAUNCHA_BUSTA']}",
    "{label:'Nob',weaponIds:['KOMBI_SKORCHA_SHOOTA','KOMBI_SKORCHA_SKORCHA']}",
    "name.textContent=String(weapon.name||weapon.weaponId||'')+(qty>0?' ×'+String(qty):'');",
    "row.classList.toggle('weapon-active',active);",
    "row.classList.toggle('weapon-muted',muted);",
    "renderBoyzNewViewSubunits(activeData);return",
    'function syncExpandedLayout(expansionRows)',
    'function syncNewViewFrameHeight()',
]:
    if required not in final_view:
        raise SystemExit('V31.114 Boyz New View acceptance failed: ' + required)
for forbidden in ['BOYZ_UNIFIED_EDIT_WEAPONS','addBoyzUnifiedEditWeaponRows','unified-edit-weapon-count']:
    if forbidden in text:
        raise SystemExit('V31.114 retained rejected Edit flat-list code: ' + forbidden)
for required in [
    '<title>WH40k 11th V31.114</title>',
    'The current baseline is WH40k_11th_V31.114;',
    'const APP_VERSION = "31.114";',
    "version: 'V31.114',",
    'unitId: String(unit && unit.unitId || "")',
    'weaponId: String(weapon.weaponId || "")',
    'quantity: entry && unit ? getRosterWeaponQuantity(entry, unit, weapon) : 0',
    'weapons: weapons.map(weapon => {',
    'CHANGE NOTE - WH40k_11th_V31.114',
]:
    if required not in text:
        raise SystemExit('V31.114 acceptance failed: ' + required)

path.write_text(text, encoding='utf-8')
print('Built V31.114: Boyz expandable New View sub-units')
