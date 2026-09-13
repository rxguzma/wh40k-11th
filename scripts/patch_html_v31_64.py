from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.63.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')

replacements = [
    ('<title>WH40k 11th V31.63</title>', '<title>WH40k 11th V31.64</title>'),
    ('The current baseline is WH40k_11th_V31.63;', 'The current baseline is WH40k_11th_V31.64;'),
    ('const APP_VERSION = "31.63";', 'const APP_VERSION = "31.64";'),
    ("version: 'V31.63',", "version: 'V31.64',"),
]
for old, new in replacements:
    if old not in text:
        raise SystemExit('version marker missing: ' + old)
    text = text.replace(old, new, 1)

frame_pattern = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
match = frame_pattern.search(text)
if not match:
    raise SystemExit('alternate View iframe not found')
np = html.unescape(match.group(2))

# The second visible Unit row is now generic/live just like the first.
old_second = "addViewUnit(f,'view-unit-row-second','Meganobz','x5',['5\"','6','2+/5++','3','7+','1']);"
new_second = "addViewUnit(f,'view-unit-row-second','','',['','','','','','']);"
if np.count(old_second) != 1:
    raise SystemExit(f'second Unit mock: expected 1 match, found {np.count(old_second)}')
np = np.replace(old_second, new_second, 1)

# Generic active Unit styling uses the exact existing Main colors/opacity.
unit_css = '''
.view-unit-row.unit-active .view-unit-name{color:#80d6a3!important}
.view-unit-row.unit-active .view-unit-stat{color:rgba(241,243,244,.5)!important}
'''
if unit_css.strip() in np:
    raise SystemExit('generic active Unit CSS already present')
if '</style>' not in np:
    raise SystemExit('alternate View style marker missing')
np = np.replace('</style>', unit_css + '</style>', 1)

# Replace the single-Unit Nazdreg-era controller with a two-Unit Edit-order
# controller. Both rows share the same detail/Weapon panel, which moves directly
# below whichever Unit is open. Only one Unit is open at a time, matching the
# established first-row interaction and preserving compact grid expansion.
helper_start = np.index('let nazdregOpen=false;')
helper_end_marker = 'window.refreshNazdregFromParent=refreshNazdregFromParent;'
helper_end = np.index(helper_end_marker, helper_start) + len(helper_end_marker)
new_helpers = r'''let activeUnitIndex=null;
let unitDataByIndex=[null,null];
let weaponFilterMode='ALL';
let selectedWeaponIndex=null;
const weaponFilterModes=['ALL','SHOOT','MELEE','OTHER'];
const UNIT_MAX_EXPANSION_ROWS=12;
const SECOND_UNIT_AUTHORED_ROW=20;
const COLLAPSED_GRID_ROWS=28;
const FIRST_UNIT_ROW=7;
function unitRow(index){return grid.querySelector(index===0?'.view-unit-row-first':'.view-unit-row-second')}
function weaponMatchesFilter(row){
  if(weaponFilterMode==='ALL')return true;
  return String(row&&row.dataset.scope||'OTHER')===weaponFilterMode;
}
function getVisibleWeaponIndexes(){
  const indexes=[];
  for(let i=1;i<=5;i++){
    const row=grid.querySelector('.weapon-row-'+i);
    if(row&&row.dataset.liveAvailable==='true'&&weaponMatchesFilter(row))indexes.push(i);
  }
  return indexes;
}
function syncExpandedLayout(expansionRows){
  const usedRows=activeUnitIndex===null?0:Math.max(0,Number(expansionRows)||0);
  [...grid.children].forEach(el=>{
    if(el.classList.contains('grid-cell'))return;
    if(el.matches('.detail-waha,.detail-deep-strike,.weapon-header,.weapon-row,.weapon-tags'))return;
    if(!el.dataset.baseGridRow){
      const authored=parseInt(getComputedStyle(el).gridRowStart,10);
      if(Number.isFinite(authored)&&authored>=SECOND_UNIT_AUTHORED_ROW)el.dataset.baseGridRow=String(authored);
    }
    const base=parseInt(el.dataset.baseGridRow||'',10);
    if(!Number.isFinite(base))return;
    let row=base-UNIT_MAX_EXPANSION_ROWS;
    if(activeUnitIndex===0)row+=usedRows;
    else if(activeUnitIndex===1&&base>SECOND_UNIT_AUTHORED_ROW)row+=usedRows;
    el.style.gridRow=String(row);
  });
  const activeGridRows=COLLAPSED_GRID_ROWS+usedRows;
  grid.querySelectorAll('.grid-cell').forEach(cell=>{
    const row=parseInt(cell.style.gridRow||'',10);
    cell.hidden=Number.isFinite(row)&&row>activeGridRows;
  });
}
function applyActiveUnitDetails(){
  const data=activeUnitIndex===null?null:unitDataByIndex[activeUnitIndex];
  const waha=grid.querySelector('.detail-waha');
  if(waha){
    const url=String(data&&data.waha||'').trim();
    waha.dataset.liveAvailable=url?'true':'false';
    waha.href=url||'#';
  }
  const weapons=data&&Array.isArray(data.weapons)?data.weapons:[];
  for(let i=1;i<=5;i++){
    const weapon=weapons[i-1]||null;
    const weaponRow=grid.querySelector('.weapon-row-'+i);
    if(weaponRow){
      weaponRow.dataset.liveAvailable=weapon?'true':'false';
      weaponRow.dataset.scope=String(weapon&&weapon.scope||'OTHER');
      if(weapon){
        const weaponName=weaponRow.querySelector('.weapon-name');
        if(weaponName)weaponName.textContent=String(weapon.name||'');
        [weapon.range,weapon.attacks,weapon.skill,weapon.strength,weapon.ap,weapon.damage].forEach((value,index)=>{const cell=weaponRow.querySelector('.wr'+(index+1));if(cell)cell.textContent=String(value??'')});
      }
      if(weaponRow.dataset.selectBound!=='true'){
        weaponRow.dataset.selectBound='true';
        weaponRow.onclick=e=>{e.stopPropagation();selectWeapon(i)};
      }
    }
    const tagRow=grid.querySelector('.weapon-tags-'+i);
    if(tagRow){
      const tags=weapon&&Array.isArray(weapon.tags)?weapon.tags:[];
      tagRow.dataset.liveAvailable=tags.length?'true':'false';
      const tagEls=[...tagRow.querySelectorAll('.weapon-tag')];
      tagEls.forEach((el,index)=>{el.textContent=String(tags[index]||'');el.style.display=tags[index]?'inline-flex':'none'});
    }
  }
}
function syncWeaponLayout(){
  const filterButton=grid.querySelector('.view-filter-toggle');
  if(filterButton)filterButton.textContent=weaponFilterMode;
  const header=grid.querySelector('.weapon-header');
  const visible=getVisibleWeaponIndexes();
  if(selectedWeaponIndex!==null&&!visible.includes(selectedWeaponIndex))selectedWeaponIndex=null;
  const ordered=selectedWeaponIndex===null?visible:[selectedWeaponIndex,...visible.filter(i=>i!==selectedWeaponIndex)];
  const hasSelection=selectedWeaponIndex!==null&&visible.includes(selectedWeaponIndex);
  grid.querySelectorAll('.detail-waha,.detail-deep-strike').forEach(el=>{el.classList.remove('keyword-muted');el.classList.toggle('detail-row-muted',hasSelection)});
  const showWeapons=Boolean(activeUnitIndex!==null&&ordered.length);
  const activeRow=activeUnitIndex===1?FIRST_UNIT_ROW+1:FIRST_UNIT_ROW;
  const detailStartRow=activeRow+1;
  if(header){
    header.style.display=showWeapons?'grid':'none';
    header.style.gridRow=String(detailStartRow+1);
  }
  let nextRow=detailStartRow+2;
  for(let i=1;i<=5;i++){
    const weaponRow=grid.querySelector('.weapon-row-'+i);
    const tagRow=grid.querySelector('.weapon-tags-'+i);
    if(weaponRow){weaponRow.style.display='none';weaponRow.classList.remove('weapon-muted','weapon-active')}
    if(tagRow){tagRow.style.display='none';tagRow.classList.remove('weapon-muted')}
  }
  if(showWeapons){
    ordered.forEach(i=>{
      const weaponRow=grid.querySelector('.weapon-row-'+i);
      const tagRow=grid.querySelector('.weapon-tags-'+i);
      if(!weaponRow)return;
      weaponRow.style.gridRow=String(nextRow++);
      weaponRow.style.display='grid';
      const active=hasSelection&&i===selectedWeaponIndex;
      const muted=hasSelection&&!active;
      weaponRow.classList.toggle('weapon-active',active);
      weaponRow.classList.toggle('weapon-muted',muted);
      if(tagRow&&tagRow.dataset.liveAvailable==='true'){
        tagRow.style.gridRow=String(nextRow++);
        tagRow.style.display='grid';
        tagRow.classList.toggle('weapon-muted',muted);
      }
    });
  }
  const expansionRows=activeUnitIndex===null?0:(showWeapons?nextRow-detailStartRow:1);
  syncExpandedLayout(expansionRows);
}
function cycleWeaponFilter(){
  const index=weaponFilterModes.indexOf(weaponFilterMode);
  weaponFilterMode=weaponFilterModes[(index+1)%weaponFilterModes.length];
  selectedWeaponIndex=null;
  syncWeaponLayout();
}
function selectWeapon(index){
  selectedWeaponIndex=selectedWeaponIndex===index?null:index;
  syncWeaponLayout();
}
function syncUnitDetailVisibility(){
  for(let index=0;index<2;index++){
    const row=unitRow(index);
    if(row)row.classList.toggle('unit-active',activeUnitIndex===index);
  }
  const statHeader=grid.querySelector('.view-stat-header');
  if(statHeader)statHeader.classList.toggle('unit-active',activeUnitIndex!==null);
  const activeRow=activeUnitIndex===1?FIRST_UNIT_ROW+1:FIRST_UNIT_ROW;
  const detailStartRow=activeRow+1;
  const waha=grid.querySelector('.detail-waha');
  if(waha){waha.style.gridRow=String(detailStartRow);waha.style.display=activeUnitIndex!==null&&waha.dataset.liveAvailable==='true'?'inline-flex':'none'}
  const deep=grid.querySelector('.detail-deep-strike');
  if(deep){deep.style.gridRow=String(detailStartRow);deep.style.display=activeUnitIndex!==null?'flex':'none'}
  syncWeaponLayout();
}
function toggleUnitDetails(index){
  const next=activeUnitIndex===index?null:index;
  activeUnitIndex=next;
  weaponFilterMode='ALL';
  selectedWeaponIndex=null;
  applyActiveUnitDetails();
  syncUnitDetailVisibility();
}
function refreshAlternateViewUnitsFromParent(){
  for(let index=0;index<2;index++){
    const row=unitRow(index);
    if(!row)continue;
    let data=null;
    try{data=parent&&typeof parent.getAlternateViewUnitData==='function'?parent.getAlternateViewUnitData(index):null}catch(_){data=null}
    unitDataByIndex[index]=data;
    if(!data){row.style.display='none';continue}
    row.style.display='grid';
    const name=row.querySelector('.view-unit-name');
    if(name)name.textContent=String(data.name||'');
    [data.m,data.t,data.sv,data.w,data.ld,data.oc].forEach((value,statIndex)=>{const cell=row.querySelector('.s'+(statIndex+1));if(cell)cell.textContent=String(value??'')});
    if(row.dataset.toggleBound!=='true'){
      row.dataset.toggleBound='true';
      row.onclick=()=>toggleUnitDetails(index);
    }
  }
  activeUnitIndex=null;
  weaponFilterMode='ALL';
  selectedWeaponIndex=null;
  applyActiveUnitDetails();
  syncUnitDetailVisibility();
  return Boolean(unitDataByIndex[0]||unitDataByIndex[1]);
}
window.refreshAlternateViewUnitsFromParent=refreshAlternateViewUnitsFromParent;'''
np = np[:helper_start] + new_helpers + np[helper_end:]

old_refresh_call = "requestAnimationFrame(refreshNazdregFromParent)"
if np.count(old_refresh_call) != 1:
    raise SystemExit(f'View refresh call: expected 1 match, found {np.count(old_refresh_call)}')
np = np.replace(old_refresh_call, 'requestAnimationFrame(refreshAlternateViewUnitsFromParent)', 1)

for required in [
    "let activeUnitIndex=null;",
    "let unitDataByIndex=[null,null];",
    "function toggleUnitDetails(index)",
    "parent.getAlternateViewUnitData(index)",
    "window.refreshAlternateViewUnitsFromParent=refreshAlternateViewUnitsFromParent;",
    "addViewUnit(f,'view-unit-row-second','','',['','','','','','']);",
    ".view-unit-row.unit-active .view-unit-name{color:#80d6a3!important}",
    ".view-unit-row.unit-active .view-unit-stat{color:rgba(241,243,244,.5)!important}",
]:
    if required not in np:
        raise SystemExit('alternate View check failed: ' + required)

np_srcdoc = html.escape(np, quote=True)
text = text[:match.start(2)] + np_srcdoc + text[match.end(2):]

# Parent bridge now returns Unit N from the exact Edit/roster model order. The
# first and second View rows therefore track Edit positions 1 and 2 directly.
parent_start = text.index('    window.getAlternateViewPrimaryUnitData = function() {')
parent_end = text.index('\n\n    function selectAppMode(mode) {', parent_start)
parent_helper = '''    window.getAlternateViewUnitData = function(index) {
      const roster = appEditMode && viewEditRosterDraft ? getViewEditRoster() : getActiveRoster();
      const models = getRosterEntryModels(roster).filter(item => item && !item.isSpacer && !item.isNote && !item.isDeleted && !item.isMissingUnit);
      const model = models[Math.max(0, Number(index) || 0)] || null;
      if (!model) return null;
      const stats = model.stats || {};
      const entry = model.entry || (roster && Array.isArray(roster.entries) ? roster.entries.find(item => item && item.entryId === model.entryId) : null);
      const unit = model.unit || (entry ? getUnitById(entry.unitId) : null);
      const weapons = entry && unit ? getWeaponsForRosterEntry(entry, unit).filter(item => item && !item.isMissingLink) : [];
      return {
        name: String(model.displayName || (model.unit && model.unit.name) || ""),
        m: String(stats.m ?? ""),
        t: String(stats.t ?? ""),
        sv: String(stats.sv ?? ""),
        w: String(stats.w ?? ""),
        ld: String(stats.ld ?? ""),
        oc: String(stats.oc ?? ""),
        waha: getUnitWahapediaLink(unit),
        weapons: weapons.slice(0,5).map(weapon => {
          const range = String(weapon.range ?? "").trim();
          const melee = range === "-" || range.toLowerCase() === "melee" || /\\(melee\\)/i.test(String(weapon.name || ""));
          const scope = melee ? "MELEE" : (range ? "SHOOT" : "OTHER");
          return {
            name: String(weapon.name || weapon.weaponId || ""),
            range,
            attacks: String(weapon.attacks ?? ""),
            skill: String(weapon.skill ?? ""),
            strength: String(weapon.strength ?? ""),
            ap: String(weapon.ap ?? ""),
            damage: String(weapon.damage ?? ""),
            tags: splitWeaponAbilities(weapon.weaponAbility),
            scope
          };
        })
      };
    };'''
text = text[:parent_start] + parent_helper + text[parent_end:]

old_show_refresh = '''        if (npWindow && typeof npWindow.refreshNazdregFromParent === "function") npWindow.refreshNazdregFromParent();'''
new_show_refresh = '''        if (npWindow && typeof npWindow.refreshAlternateViewUnitsFromParent === "function") npWindow.refreshAlternateViewUnitsFromParent();'''
if text.count(old_show_refresh) != 1:
    raise SystemExit(f'alternate View open refresh: expected 1 match, found {text.count(old_show_refresh)}')
text = text.replace(old_show_refresh, new_show_refresh, 1)

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.64
    Scope: Wire the second alternate-View Unit to the second real Unit in current Edit/roster order. The second Unit now has the same live name/stats, open/collapse behavior, Waha link, ALL/SHOOT/MELEE/OTHER filtering, compact Weapon rows, Weapon selection, selected-green styling, inactive 50% styling, Tag/detail-row treatment, and dynamic expansion behavior as the first Unit. The shared detail panel appears directly below whichever of the first two Units is open; only one is open at a time. Reordering Edit changes both first and second View positions automatically.
    Risk areas: Alternate View first-two Unit wiring and shared expansion placement only. Canonical View/Edit/Cards, roster persistence, and combat behavior are unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.63\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

text = re.sub(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.59\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)

checks = [
    '<title>WH40k 11th V31.64</title>',
    'const APP_VERSION = "31.64";',
    "version: 'V31.64',",
    'window.getAlternateViewUnitData = function(index)',
    'getRosterEntryModels(roster).filter',
    'refreshAlternateViewUnitsFromParent',
    'CHANGE NOTE - WH40k_11th_V31.64',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('acceptance check failed: ' + ', '.join(missing))
if 'window.getAlternateViewPrimaryUnitData = function()' in text:
    raise SystemExit('old single-Unit parent bridge still present')

out.write_text(text, encoding='utf-8')
print('Built V31.64: first two alternate-View Units follow Edit order and share identical behavior')
