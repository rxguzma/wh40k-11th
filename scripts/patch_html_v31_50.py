from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.49.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def r(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


r('<title>WH40k 11th V31.49</title>', '<title>WH40k 11th V31.50</title>', 'title')
r('The current baseline is WH40k_11th_V31.49;', 'The current baseline is WH40k_11th_V31.50;', 'baseline')
r('const APP_VERSION = "31.49";', 'const APP_VERSION = "31.50";', 'APP_VERSION')
r("version: 'V31.49',", "version: 'V31.50',", 'quality version')

frame_pattern = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
match = frame_pattern.search(text)
if not match:
    raise SystemExit('alternate View iframe not found')
np = html.unescape(match.group(2))


def nr(old: str, new: str, label: str) -> None:
    global np
    count = np.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    np = np.replace(old, new, 1)


# Lines 5 and 6 are intentionally empty: shorten the header shell to row 4
# and remove the old phase-button row.
nr('.top-header-shell{grid-column:1/span 16;grid-row:1/span 5;', '.top-header-shell{grid-column:1/span 16;grid-row:1/span 4;', 'header shell rows 1-4')

header_start = np.index('function addViewHeader(f){')
header_end = np.index('function addViewStatHeader(f){', header_start)
new_header = """function addViewHeader(f){const sh=document.createElement('div');sh.className='top-header-shell';f.appendChild(sh);const n=document.createElement('div');n.className='top-roster-name';n.textContent='Winning ORKS';f.appendChild(n);const d=document.createElement('div');d.className='top-detachments';d.textContent='Bully Boyz - Da Big Hunt - Wreckas';f.appendChild(d);const s=document.createElement('div');s.className='top-summary';const a=document.createElement('span');a.className='top-summary-disposition';a.textContent='Priority Assets';const z=document.createElement('span');z.className='top-summary-rest';z.textContent='- 1995 pts - 10 VPs';s.append(a,z);f.appendChild(s);const gb=document.createElement('button');gb.type='button';gb.className='button-standard grid-toggle';gb.textContent='G';gb.setAttribute('aria-label','Toggle grid');gb.setAttribute('aria-pressed','false');gb.onclick=()=>{const on=!grid.classList.contains('grid-on');grid.classList.toggle('grid-on',on);gb.classList.toggle('active-green',on);gb.setAttribute('aria-pressed',on?'true':'false')};f.appendChild(gb);const fb=document.createElement('button');fb.type='button';fb.className='button-standard active-green view-filter-toggle';fb.textContent=weaponFilterMode;fb.setAttribute('aria-label','Weapon filter');fb.onclick=cycleWeaponFilter;f.appendChild(fb)}
"""
np = np[:header_start] + new_header + np[header_end:]

# Position controls exactly on row 4.
nr(
    '.grid-toggle{grid-column:1;grid-row:6;z-index:102;align-self:center;justify-self:center;width:var(--std)!important;height:var(--std)!important;padding:0!important}',
    '.grid-toggle{grid-column:13;grid-row:4;z-index:102;align-self:center;justify-self:center;width:var(--std)!important;height:var(--std)!important;padding:0!important}',
    'Grid toggle M4',
)
filter_css = ".view-filter-toggle{grid-column:14/span 3;grid-row:4;z-index:102;align-self:center;justify-self:center}\n"
if filter_css.strip() in np:
    raise SystemExit('filter CSS already present')
np = np.replace('.draft-grid{border-top:0;border-left:0}', filter_css + '.draft-grid{border-top:0;border-left:0}', 1)

# Nazdreg detail tags: Waha first (A:C), Deep Strike second (D:F).
np, count = re.subn(
    r'\.detail-waha\{[^}]*\}',
    '.detail-waha{grid-column:1/span 3;grid-row:10;z-index:3;align-self:center;justify-self:center;text-decoration:none}',
    np,
    count=1,
)
if count != 1:
    raise SystemExit(f'Waha position/style: expected 1 match, found {count}')
nr(
    '.detail-deep-strike{grid-column:1/span 3;grid-row:10;',
    '.detail-deep-strike{grid-column:4/span 3;grid-row:10;',
    'Deep Strike second tag position',
)

# Put all five Nazdreg Weapon/Tag pairs on consecutive new lines.
old_weapon_rows = '.weapon-row-1{grid-row:11}.weapon-tags-1{grid-row:12}.weapon-row-2{grid-row:31}.weapon-tags-2{grid-row:32}.weapon-row-3{grid-row:34}.weapon-tags-3{grid-row:35}.weapon-row-4{grid-row:37}.weapon-tags-4{grid-row:38}.weapon-row-5{grid-row:40}.weapon-tags-5{grid-row:41}'
new_weapon_rows = '.weapon-row-1{grid-row:11}.weapon-tags-1{grid-row:12}.weapon-row-2{grid-row:13}.weapon-tags-2{grid-row:14}.weapon-row-3{grid-row:15}.weapon-tags-3{grid-row:16}.weapon-row-4{grid-row:17}.weapon-tags-4{grid-row:18}.weapon-row-5{grid-row:19}.weapon-tags-5{grid-row:20}'
nr(old_weapon_rows, new_weapon_rows, 'all Nazdreg Weapon rows 11-20')
nr('.view-unit-row-second{grid-row:20}', '.view-unit-row-second{grid-row:21}', 'Meganobz row 21')

# Active unit treatment: keep the existing green name and apply a 50% active-green
# background only to I8:P9 (stat header + Nazdreg stat cells). Hide all live detail
# lines until Nazdreg is toggled on.
old_toggle_css = """.view-unit-row-first.unit-active .view-unit-name{color:#80d6a3}
.detail-deep-strike,.weapon-row-1,.weapon-tags-1{display:none}
"""
new_toggle_css = """.view-unit-row-first.unit-active .view-unit-name{color:#80d6a3}
.view-stat-header.unit-active,.view-unit-row-first.unit-active .view-unit-stat{background:rgba(31,91,53,.5)}
.detail-waha,.detail-deep-strike,.weapon-row-1,.weapon-tags-1,.weapon-row-2,.weapon-tags-2,.weapon-row-3,.weapon-tags-3,.weapon-row-4,.weapon-tags-4,.weapon-row-5,.weapon-tags-5{display:none}
"""
nr(old_toggle_css, new_toggle_css, 'active Nazdreg styling')

# Move Waha out of the old expanded header and make it a real clickable button in
# the first tag position.
old_waha_create = """  const w=document.createElement('div');w.className='detail-waha';w.textContent='Waha';h.appendChild(w);
  ['5"','7','2+/5++','8','6+','1'].forEach((v,i)=>{const s=document.createElement('div');s.className='detail-unit-stat du'+(i+1);s.textContent=v;h.appendChild(s)});f.appendChild(h);
  const ds=document.createElement('div');ds.className='detail-deep-strike';ds.textContent='DEEP STRIKE';f.appendChild(ds);"""
new_waha_create = """  ['5"','7','2+/5++','8','6+','1'].forEach((v,i)=>{const s=document.createElement('div');s.className='detail-unit-stat du'+(i+1);s.textContent=v;h.appendChild(s)});f.appendChild(h);
  const w=document.createElement('a');w.className='button-standard detail-waha';w.textContent='Waha';w.href='#';w.target='_blank';w.rel='noopener';w.onclick=e=>e.stopPropagation();f.appendChild(w);
  const ds=document.createElement('div');ds.className='detail-deep-strike';ds.textContent='DEEP STRIKE';f.appendChild(ds);"""
nr(old_waha_create, new_waha_create, 'move Waha to row 10')

# Replace the one-weapon toggle helper with five live Weapon rows and the N:P
# ALL -> SHOOT -> MELEE -> OTHER 3-cell carousel.
helper_start = np.index('let nazdregOpen=false;')
helper_end = np.index('function refreshNazdregFromParent(){', helper_start)
new_helpers = """let nazdregOpen=false;
let weaponFilterMode='ALL';
const weaponFilterModes=['ALL','SHOOT','MELEE','OTHER'];
function weaponMatchesFilter(row){
  if(weaponFilterMode==='ALL')return true;
  return String(row&&row.dataset.scope||'OTHER')===weaponFilterMode;
}
function syncWeaponFilter(){
  const filterButton=grid.querySelector('.view-filter-toggle');
  if(filterButton)filterButton.textContent=weaponFilterMode;
  for(let i=1;i<=5;i++){
    const weaponRow=grid.querySelector('.weapon-row-'+i);
    const tagRow=grid.querySelector('.weapon-tags-'+i);
    const showWeapon=Boolean(nazdregOpen&&weaponRow&&weaponRow.dataset.liveAvailable==='true'&&weaponMatchesFilter(weaponRow));
    if(weaponRow)weaponRow.style.display=showWeapon?'grid':'none';
    if(tagRow)tagRow.style.display=showWeapon&&tagRow.dataset.liveAvailable==='true'?'grid':'none';
  }
}
function cycleWeaponFilter(){
  const index=weaponFilterModes.indexOf(weaponFilterMode);
  weaponFilterMode=weaponFilterModes[(index+1)%weaponFilterModes.length];
  syncWeaponFilter();
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
  syncWeaponFilter();
}
function toggleNazdregDetails(){
  nazdregOpen=!nazdregOpen;
  syncNazdregDetailVisibility();
}
"""
np = np[:helper_start] + new_helpers + np[helper_end:]

refresh_start = np.index('function refreshNazdregFromParent(){')
refresh_end_marker = 'window.refreshNazdregFromParent=refreshNazdregFromParent;'
refresh_end = np.index(refresh_end_marker, refresh_start) + len(refresh_end_marker)
new_refresh = """function refreshNazdregFromParent(){
  const row=grid.querySelector('.view-unit-row-first');
  if(!row)return false;
  let data=null;
  try{data=parent&&typeof parent.getAlternateViewNazdregData==='function'?parent.getAlternateViewNazdregData():null}catch(_){data=null}
  if(!data){nazdregOpen=false;row.style.display='none';syncNazdregDetailVisibility();return false}
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
  syncNazdregDetailVisibility();
  return true;
}
window.refreshNazdregFromParent=refreshNazdregFromParent;"""
np = np[:refresh_start] + new_refresh + np[refresh_end:]

np_checks = [
    'grid-row:1/span 4',
    'grid-column:13;grid-row:4',
    'view-filter-toggle{grid-column:14/span 3;grid-row:4',
    '.detail-waha{grid-column:1/span 3;grid-row:10',
    '.detail-deep-strike{grid-column:4/span 3;grid-row:10',
    '.weapon-row-5{grid-row:19}.weapon-tags-5{grid-row:20}',
    '.view-unit-row-second{grid-row:21}',
    'background:rgba(31,91,53,.5)',
    "const weaponFilterModes=['ALL','SHOOT','MELEE','OTHER'];",
    'function cycleWeaponFilter()',
    "waha.href=url||'#';",
    'for(let i=1;i<=5;i++)',
]
missing_np = [value for value in np_checks if value not in np]
if missing_np:
    raise SystemExit('alternate View checks failed: ' + ', '.join(missing_np))
if "['COMMAND','MOVE','SHOOT','CHARGE','FIGHT']" in np:
    raise SystemExit('phase buttons still present on row 6')

np_srcdoc = html.escape(np, quote=True)
text = text[:match.start(2)] + np_srcdoc + text[match.end(2):]

# Return the real Edit/active-roster Waha URL plus all five live Nazdreg weapons.
bridge_start = text.index('      const weapons = entry && unit ? getWeaponsForRosterEntry(entry, unit).filter(item => item && !item.isMissingLink) : [];')
bridge_end = text.index('\n\n    function selectAppMode(mode) {', bridge_start)
new_bridge_tail = """      const weapons = entry && unit ? getWeaponsForRosterEntry(entry, unit).filter(item => item && !item.isMissingLink) : [];
      return {
        name: String(model.displayName || (model.unit && model.unit.name) || "Nazdreg"),
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
    };"""
text = text[:bridge_start] + new_bridge_tail + text[bridge_end:]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.50
    Scope: Refine the alternate View Nazdreg layout. Rows 5 and 6 are cleared and the header shell ends at row 4. Move the Grid toggle to M4 and add one three-cell N4:P4 filter carousel cycling ALL, SHOOT, MELEE, OTHER. Move Waha to the first row-10 tag position A:C, move Deep Strike to D:F, and wire Waha to the same real Unit Wahapedia URL used by Edit. When Nazdreg is toggled on, keep its active green name and apply a 50%-alpha active-green treatment only across I8:P9. Wire all five real Nazdreg Weapon profiles and Weapon Ability labels from the active/Edit roster into consecutive Weapon/Tag rows 11-20; move Meganobz to row 21. The filter carousel shows the live Weapon rows matching ALL, SHOOT, MELEE, or OTHER while the Unit is open.
    Risk areas: Alternate View header rows 4-6, Nazdreg toggle styling, Waha link, Weapon rows 11-20, and the existing Nazdreg parent bridge only. Canonical View/Edit/Cards, roster persistence, and combat behavior are unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.49\n'
if mark not in text:
    raise SystemExit('release note marker missing')
text = text.replace(mark, note + mark, 1)
text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.45\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

checks = [
    '<title>WH40k 11th V31.50</title>',
    'const APP_VERSION = "31.50";',
    "version: 'V31.50',",
    'waha: getUnitWahapediaLink(unit)',
    'weapons: weapons.slice(0,5).map',
    'const scope = melee ? "MELEE" : (range ? "SHOOT" : "OTHER");',
    'view-filter-toggle{grid-column:14/span 3;grid-row:4',
    'background:rgba(31,91,53,.5)',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))

out.write_text(text, encoding='utf-8')
print('Built V31.50 alternate View Waha, filter, active highlight, and all Nazdreg weapons')
