from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.54.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def r(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


r('<title>WH40k 11th V31.54</title>', '<title>WH40k 11th V31.55</title>', 'title')
r('The current baseline is WH40k_11th_V31.54;', 'The current baseline is WH40k_11th_V31.55;', 'baseline')
r('const APP_VERSION = "31.54";', 'const APP_VERSION = "31.55";', 'APP_VERSION')
r("version: 'V31.54',", "version: 'V31.55',", 'quality version')

frame_pattern = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
match = frame_pattern.search(text)
if not match:
    raise SystemExit('alternate View iframe not found')
np = html.unescape(match.group(2))

# Muted Weapon treatment: only font treatment changes. Non-selected Weapon text
# uses 75% opacity; non-selected Weapon Tag text uses Main's muted gray.
mute_css = """
.weapon-row.weapon-muted .weapon-name,.weapon-row.weapon-muted .weapon-stat{color:rgba(241,243,244,.75)}
.weapon-tags.weapon-muted .weapon-tag{color:var(--muted)}
"""
if mute_css.strip() in np:
    raise SystemExit('weapon mute CSS already present')
if '</style>' not in np:
    raise SystemExit('alternate View style close marker missing')
np = np.replace('</style>', mute_css + '</style>', 1)

# Replace the fixed-row filter/expansion behavior with compact dynamic stacking.
# Row 8 remains Waha / Deep Strike. The Weapon header is row 9 only when at
# least one Weapon matches the current filter. Visible Weapons then stack from
# row 10 with no blank rows. Selecting a Weapon moves it to row 10 and mutes
# the other visible Weapons without hiding them.
helper_start = np.index('let nazdregOpen=false;')
helper_end = np.index('function refreshNazdregFromParent(){', helper_start)
new_helpers = """let nazdregOpen=false;
let weaponFilterMode='ALL';
let selectedWeaponIndex=null;
const weaponFilterModes=['ALL','SHOOT','MELEE','OTHER'];
const NAZDREG_MAX_EXPANSION_ROWS=12;
const NAZDREG_DOWNSTREAM_BASE_ROW=20;
const NAZDREG_COLLAPSED_GRID_ROWS=28;
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
function syncNazdregExpandedLayout(expansionRows){
  const usedRows=nazdregOpen?Math.max(0,Number(expansionRows)||0):0;
  const pullUp=NAZDREG_MAX_EXPANSION_ROWS-usedRows;
  [...grid.children].forEach(el=>{
    if(el.classList.contains('grid-cell'))return;
    if(el.matches('.detail-waha,.detail-deep-strike,.weapon-header,.weapon-row,.weapon-tags'))return;
    if(!el.dataset.baseGridRow){
      const authored=parseInt(getComputedStyle(el).gridRowStart,10);
      if(Number.isFinite(authored)&&authored>=NAZDREG_DOWNSTREAM_BASE_ROW)el.dataset.baseGridRow=String(authored);
    }
    const base=parseInt(el.dataset.baseGridRow||'',10);
    if(Number.isFinite(base))el.style.gridRow=String(base-pullUp);
  });
  const activeGridRows=NAZDREG_COLLAPSED_GRID_ROWS+usedRows;
  grid.querySelectorAll('.grid-cell').forEach(cell=>{
    const row=parseInt(cell.style.gridRow||'',10);
    cell.hidden=Number.isFinite(row)&&row>activeGridRows;
  });
}
function syncWeaponLayout(){
  const filterButton=grid.querySelector('.view-filter-toggle');
  if(filterButton)filterButton.textContent=weaponFilterMode;
  const header=grid.querySelector('.weapon-header');
  const visible=getVisibleWeaponIndexes();
  if(selectedWeaponIndex!==null&&!visible.includes(selectedWeaponIndex))selectedWeaponIndex=null;
  const ordered=selectedWeaponIndex===null?visible:[selectedWeaponIndex,...visible.filter(i=>i!==selectedWeaponIndex)];
  const hasSelection=selectedWeaponIndex!==null&&visible.includes(selectedWeaponIndex);
  const showWeapons=Boolean(nazdregOpen&&ordered.length);
  if(header){
    header.style.display=showWeapons?'grid':'none';
    header.style.gridRow='9';
  }
  let nextRow=10;
  for(let i=1;i<=5;i++){
    const weaponRow=grid.querySelector('.weapon-row-'+i);
    const tagRow=grid.querySelector('.weapon-tags-'+i);
    if(weaponRow){weaponRow.style.display='none';weaponRow.classList.remove('weapon-muted')}
    if(tagRow){tagRow.style.display='none';tagRow.classList.remove('weapon-muted')}
  }
  if(showWeapons){
    ordered.forEach(i=>{
      const weaponRow=grid.querySelector('.weapon-row-'+i);
      const tagRow=grid.querySelector('.weapon-tags-'+i);
      if(!weaponRow)return;
      weaponRow.style.gridRow=String(nextRow++);
      weaponRow.style.display='grid';
      const muted=hasSelection&&i!==selectedWeaponIndex;
      weaponRow.classList.toggle('weapon-muted',muted);
      if(tagRow&&tagRow.dataset.liveAvailable==='true'){
        tagRow.style.gridRow=String(nextRow++);
        tagRow.style.display='grid';
        tagRow.classList.toggle('weapon-muted',muted);
      }
    });
  }
  const expansionRows=nazdregOpen?(showWeapons?nextRow-8:1):0;
  syncNazdregExpandedLayout(expansionRows);
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
function syncNazdregDetailVisibility(){
  const row=grid.querySelector('.view-unit-row-first');
  const statHeader=grid.querySelector('.view-stat-header');
  if(row)row.classList.toggle('unit-active',nazdregOpen);
  if(statHeader)statHeader.classList.toggle('unit-active',nazdregOpen);
  const waha=grid.querySelector('.detail-waha');
  if(waha)waha.style.display=nazdregOpen&&waha.dataset.liveAvailable==='true'?'inline-flex':'none';
  const deep=grid.querySelector('.detail-deep-strike');
  if(deep)deep.style.display=nazdregOpen?'flex':'none';
  syncWeaponLayout();
}
function toggleNazdregDetails(){
  nazdregOpen=!nazdregOpen;
  if(!nazdregOpen)selectedWeaponIndex=null;
  syncNazdregDetailVisibility();
}
"""
np = np[:helper_start] + new_helpers + np[helper_end:]

# Rebuild the live refresh so each real Weapon row is selectable. The selected
# Weapon is a presentation state only; underlying Edit/roster data is unchanged.
refresh_start = np.index('function refreshNazdregFromParent(){')
refresh_end_marker = 'window.refreshNazdregFromParent=refreshNazdregFromParent;'
refresh_end = np.index(refresh_end_marker, refresh_start) + len(refresh_end_marker)
new_refresh = """function refreshNazdregFromParent(){
  const row=grid.querySelector('.view-unit-row-first');
  if(!row)return false;
  let data=null;
  try{data=parent&&typeof parent.getAlternateViewNazdregData==='function'?parent.getAlternateViewNazdregData():null}catch(_){data=null}
  if(!data){nazdregOpen=false;selectedWeaponIndex=null;row.style.display='none';syncNazdregDetailVisibility();return false}
  row.style.display='grid';
  const name=row.querySelector('.view-unit-name');
  if(name)name.textContent=String(data.name||'Nazdreg');
  [data.m,data.t,data.sv,data.w,data.ld,data.oc].forEach((value,index)=>{const cell=row.querySelector('.s'+(index+1));if(cell)cell.textContent=String(value??'')});
  const waha=grid.querySelector('.detail-waha');
  if(waha){
    const url=String(data.waha||'').trim();
    waha.dataset.liveAvailable=url?'true':'false';
    waha.href=url||'#';
  }
  const weapons=Array.isArray(data.weapons)?data.weapons:[];
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
  if(row.dataset.toggleBound!=='true'){row.dataset.toggleBound='true';row.onclick=toggleNazdregDetails}
  nazdregOpen=false;
  weaponFilterMode='ALL';
  selectedWeaponIndex=null;
  syncNazdregDetailVisibility();
  return true;
}
window.refreshNazdregFromParent=refreshNazdregFromParent;"""
np = np[:refresh_start] + new_refresh + np[refresh_end:]

np_checks = [
    ".weapon-row.weapon-muted .weapon-name,.weapon-row.weapon-muted .weapon-stat{color:rgba(241,243,244,.75)}",
    ".weapon-tags.weapon-muted .weapon-tag{color:var(--muted)}",
    "let selectedWeaponIndex=null;",
    "function getVisibleWeaponIndexes()",
    "header.style.display=showWeapons?'grid':'none';",
    "header.style.gridRow='9';",
    "let nextRow=10;",
    "weaponRow.style.gridRow=String(nextRow++);",
    "tagRow.style.gridRow=String(nextRow++);",
    "function selectWeapon(index)",
    "weaponRow.onclick=e=>{e.stopPropagation();selectWeapon(i)};",
    "const activeGridRows=NAZDREG_COLLAPSED_GRID_ROWS+usedRows;",
]
missing_np = [value for value in np_checks if value not in np]
if missing_np:
    raise SystemExit('alternate View checks failed: ' + ', '.join(missing_np))
if 'const NAZDREG_EXPANSION_ROWS=12;' in np:
    raise SystemExit('old fixed expansion constant still present')

np_srcdoc = html.escape(np, quote=True)
text = text[:match.start(2)] + np_srcdoc + text[match.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.55
    Scope: Make alternate-View Weapon filtering and selection use compact dynamic rows. The Weapon stat header at row 9 now exists only when the open Unit has at least one Weapon visible under the current ALL/SHOOT/MELEE/OTHER filter. Visible Weapon and Tag rows stack continuously from row 10 with no reserved gaps, and downstream rows move up or down to match the actual expansion height. Tapping a visible Weapon selects it, moves it to row 10, leaves the other matching Weapons visible, mutes their Weapon text to 75% opacity, and changes their Tag text to Main muted gray. Tapping the selected Weapon again clears selection and restores normal ordering. This establishes the interaction pattern to reuse for each Unit as additional Units are wired.
    Risk areas: Alternate View Weapon filtering, Weapon selection presentation, and dynamic expansion height only. Live Weapon/Waha data, canonical View/Edit/Cards, roster persistence, and combat behavior are unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.54\n'
if mark not in text:
    raise SystemExit('release note marker missing')
text = text.replace(mark, note + mark, 1)
text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.50\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

checks = [
    '<title>WH40k 11th V31.55</title>',
    'const APP_VERSION = "31.55";',
    "version: 'V31.55',",
    'weapon-row weapon-muted',
    'selectedWeaponIndex',
    'const NAZDREG_MAX_EXPANSION_ROWS=12;',
]
# The muted class is added dynamically, so its literal static class pair is not
# expected in source; verify the actual dynamic class toggle instead.
checks.remove('weapon-row weapon-muted')
checks.append("weaponRow.classList.toggle('weapon-muted',muted);")
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))

out.write_text(text, encoding='utf-8')
print('Built V31.55 with compact Weapon reflow and selectable Weapon muting')
