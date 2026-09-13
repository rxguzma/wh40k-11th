from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.52.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def r(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


r('<title>WH40k 11th V31.52</title>', '<title>WH40k 11th V31.53</title>', 'title')
r('The current baseline is WH40k_11th_V31.52;', 'The current baseline is WH40k_11th_V31.53;', 'baseline')
r('const APP_VERSION = "31.52";', 'const APP_VERSION = "31.53";', 'APP_VERSION')
r("version: 'V31.52',", "version: 'V31.53',", 'quality version')

frame_pattern = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
match = frame_pattern.search(text)
if not match:
    raise SystemExit('alternate View iframe not found')
np = html.unescape(match.group(2))

# Treat the Nazdreg details as a real expanding block rather than fixed blank
# rows whose contents merely appear/disappear. Closed: everything that normally
# begins at row 20 or lower shifts up by 12 rows. Open: rows 8-19 are inserted
# back into the flow and all downstream content returns to its authored rows.
old_hidden = '.detail-waha,.detail-deep-strike,.weapon-row-1,.weapon-tags-1,.weapon-row-2,.weapon-tags-2,.weapon-row-3,.weapon-tags-3,.weapon-row-4,.weapon-tags-4,.weapon-row-5,.weapon-tags-5{display:none}'
new_hidden = '.detail-waha,.detail-deep-strike,.weapon-header,.weapon-row-1,.weapon-tags-1,.weapon-row-2,.weapon-tags-2,.weapon-row-3,.weapon-tags-3,.weapon-row-4,.weapon-tags-4,.weapon-row-5,.weapon-tags-5{display:none}'
if np.count(old_hidden) != 1:
    raise SystemExit(f'hidden detail selector: expected 1 match, found {np.count(old_hidden)}')
np = np.replace(old_hidden, new_hidden, 1)

helper_start = np.index('let nazdregOpen=false;')
helper_end = np.index('function refreshNazdregFromParent(){', helper_start)
new_helpers = """let nazdregOpen=false;
let weaponFilterMode='ALL';
const weaponFilterModes=['ALL','SHOOT','MELEE','OTHER'];
const NAZDREG_EXPANSION_ROWS=12;
const NAZDREG_DOWNSTREAM_BASE_ROW=20;
const NAZDREG_COLLAPSED_GRID_ROWS=28;
function weaponMatchesFilter(row){
  if(weaponFilterMode==='ALL')return true;
  return String(row&&row.dataset.scope||'OTHER')===weaponFilterMode;
}
function syncNazdregExpandedLayout(){
  [...grid.children].forEach(el=>{
    if(el.classList.contains('grid-cell'))return;
    if(el.matches('.detail-waha,.detail-deep-strike,.weapon-header,.weapon-row,.weapon-tags'))return;
    if(!el.dataset.baseGridRow){
      const authored=parseInt(getComputedStyle(el).gridRowStart,10);
      if(Number.isFinite(authored)&&authored>=NAZDREG_DOWNSTREAM_BASE_ROW)el.dataset.baseGridRow=String(authored);
    }
    const base=parseInt(el.dataset.baseGridRow||'',10);
    if(Number.isFinite(base))el.style.gridRow=String(nazdregOpen?base:base-NAZDREG_EXPANSION_ROWS);
  });
  grid.querySelectorAll('.grid-cell').forEach(cell=>{
    const row=parseInt(cell.style.gridRow||'',10);
    cell.hidden=!nazdregOpen&&Number.isFinite(row)&&row>NAZDREG_COLLAPSED_GRID_ROWS;
  });
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
  const weaponHeader=grid.querySelector('.weapon-header');
  if(weaponHeader)weaponHeader.style.display=nazdregOpen?'grid':'none';
  syncWeaponFilter();
  syncNazdregExpandedLayout();
}
function toggleNazdregDetails(){
  nazdregOpen=!nazdregOpen;
  syncNazdregDetailVisibility();
}
"""
np = np[:helper_start] + new_helpers + np[helper_end:]

np_checks = [
    'const NAZDREG_EXPANSION_ROWS=12;',
    'const NAZDREG_DOWNSTREAM_BASE_ROW=20;',
    'const NAZDREG_COLLAPSED_GRID_ROWS=28;',
    "if(el.matches('.detail-waha,.detail-deep-strike,.weapon-header,.weapon-row,.weapon-tags'))return;",
    'el.style.gridRow=String(nazdregOpen?base:base-NAZDREG_EXPANSION_ROWS);',
    'cell.hidden=!nazdregOpen&&Number.isFinite(row)&&row>NAZDREG_COLLAPSED_GRID_ROWS;',
    "if(weaponHeader)weaponHeader.style.display=nazdregOpen?'grid':'none';",
    '.weapon-header{grid-row:11;',
    '.view-unit-row-second{grid-row:20}',
]
missing_np = [value for value in np_checks if value not in np]
if missing_np:
    raise SystemExit('alternate View checks failed: ' + ', '.join(missing_np))

np_srcdoc = html.escape(np, quote=True)
text = text[:match.start(2)] + np_srcdoc + text[match.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.53
    Scope: Change the alternate View Nazdreg interaction from fixed reserved rows with show/hide content to a true expanding layout. In the collapsed state, downstream content moves up 12 rows so the next unit follows Nazdreg directly. Tapping Nazdreg expands rows 8-19 in place, restores downstream content to its authored rows, and shows Waha, Deep Strike, the Weapon stat header at I11:P11, and the live weapon/tag rows. Tapping again collapses those 12 rows and pulls downstream content back up.
    Risk areas: Alternate View Nazdreg expansion/collapse geometry only. Live data wiring, Waha links, weapon filters, canonical View/Edit/Cards, persistence, and combat behavior are unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.52\n'
if mark not in text:
    raise SystemExit('release note marker missing')
text = text.replace(mark, note + mark, 1)
text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.48\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

checks = [
    '<title>WH40k 11th V31.53</title>',
    'const APP_VERSION = "31.53";',
    "version: 'V31.53',",
    'const NAZDREG_EXPANSION_ROWS=12;',
    '.weapon-header{grid-row:11;',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))

out.write_text(text, encoding='utf-8')
print('Built V31.53 with true 12-row Nazdreg expansion')
