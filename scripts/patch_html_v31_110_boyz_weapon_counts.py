from pathlib import Path
import csv
import html
import json
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
once('<title>WH40k 11th V31.109</title>', '<title>WH40k 11th V31.110</title>', 'title')
once('The current baseline is WH40k_11th_V31.109;', 'The current baseline is WH40k_11th_V31.110;', 'baseline')
once('const APP_VERSION = "31.109";', 'const APP_VERSION = "31.110";', 'APP_VERSION')
once("version: 'V31.109',", "version: 'V31.110',", 'quality version')

# Build the Boyz flat weapon/count contract directly from the current CSVs.
# This pass intentionally does not consume Weapon_Sections or loadout CSVs.
data_root = Path('data/orks')
with (data_root / 'Weapon_Quantities.csv').open(encoding='utf-8-sig', newline='') as handle:
    quantity_rows = list(csv.DictReader(handle))
with (data_root / 'Unit_Weapons.csv').open(encoding='utf-8-sig', newline='') as handle:
    unit_weapon_rows = list(csv.DictReader(handle))
with (data_root / 'Weapon_Stats.csv').open(encoding='utf-8-sig', newline='') as handle:
    stat_rows = list(csv.DictReader(handle))

boyz_order = [
    str(row.get('Weapon_ID') or '').strip()
    for row in unit_weapon_rows
    if str(row.get('Unit_ID') or '').strip().upper() == 'BOYZ'
]
if not boyz_order:
    raise SystemExit('BOYZ has no Unit_Weapons rows')

names = {
    str(row.get('Weapon_ID') or '').strip(): str(row.get('Weapon Name') or '').strip()
    for row in stat_rows
}
quantities = {}
for row in quantity_rows:
    if str(row.get('Unit_ID') or '').strip().upper() != 'BOYZ':
        continue
    weapon_id = str(row.get('Weapon_ID') or '').strip()
    size_label = str(row.get('Size_Label') or '').strip().lower()
    raw_quantity = str(row.get('Quantity') or '').strip()
    if not weapon_id or size_label not in {'x10', 'x20'}:
        continue
    try:
        quantity = int(raw_quantity)
    except ValueError:
        raise SystemExit(f'Invalid BOYZ Weapon_Quantities quantity: {weapon_id} {size_label}={raw_quantity!r}')
    quantities.setdefault(weapon_id, {})[size_label] = quantity

boyz_weapons = []
for weapon_id in boyz_order:
    weapon_quantities = quantities.get(weapon_id, {})
    if not weapon_quantities:
        continue
    if 'x10' not in weapon_quantities or 'x20' not in weapon_quantities:
        raise SystemExit(f'BOYZ weapon quantity is incomplete for {weapon_id}')
    weapon_name = names.get(weapon_id) or weapon_id.replace('_', ' ').title()
    boyz_weapons.append({
        'id': weapon_id,
        'name': weapon_name,
        'x10': weapon_quantities['x10'],
        'x20': weapon_quantities['x20'],
    })

if not boyz_weapons:
    raise SystemExit('No BOYZ weapon-count rows were built')
weapon_json = json.dumps(boyz_weapons, ensure_ascii=False, separators=(',', ':'))

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing')
view_np = html.unescape(vm.group(2))

# Add only the flat weapon/count presentation needed for this pass.
style_marker = '</style>'
if view_np.count(style_marker) < 1:
    raise SystemExit('Unified New View/Edit style close marker missing')
weapon_css = '''
.unified-edit-weapon-row{grid-column:1/span 16;min-height:var(--cell);display:flex;align-items:center;padding:0 8px;overflow:hidden;color:var(--secondary);font:700 var(--body)/1 Roboto,Arial,sans-serif;white-space:nowrap}
.unified-edit-weapon-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.unified-edit-weapon-count{flex:0 0 auto;margin-left:6px;color:var(--orange);font-weight:900}
'''
view_np = view_np.replace(style_marker, weapon_css + style_marker, 1)

render_marker = 'function renderUnifiedEditRows(rows){'
if view_np.count(render_marker) != 1:
    raise SystemExit(f'Unified Edit render marker: expected 1 match, found {view_np.count(render_marker)}')
weapon_helpers = f'''const BOYZ_UNIFIED_EDIT_WEAPONS={weapon_json};
function isBoyzUnifiedEditUnit(data){{
  const unitId=String(data&&data.unitId||data&&data.id||'').trim().toUpperCase();
  const name=String(data&&data.name||'').trim().toUpperCase();
  return unitId==='BOYZ'||name==='BOYZ';
}}
function getBoyzUnifiedEditSize(data){{
  const label=String(data&&data.pointLabel||'').trim().toLowerCase();
  return label==='x20'?'x20':label==='x10'?'x10':'';
}}
function addBoyzUnifiedEditWeaponRows(fragment,data,rowIndex,cursor){{
  if(!isBoyzUnifiedEditUnit(data))return cursor;
  const size=getBoyzUnifiedEditSize(data);
  if(!size)return cursor;
  BOYZ_UNIFIED_EDIT_WEAPONS.forEach(weapon=>{{
    const qty=Number(weapon&&weapon[size]);
    if(!Number.isFinite(qty))return;
    const row=document.createElement('div');
    row.className='dynamic-roster-row unified-edit-weapon-row';
    row.dataset.rosterIndex=String(rowIndex);
    row.dataset.weaponId=String(weapon&&weapon.id||'');
    row.style.gridRow=String(cursor++);
    const name=document.createElement('span');
    name.className='unified-edit-weapon-name';
    name.textContent=String(weapon&&weapon.name||weapon&&weapon.id||'');
    const count=document.createElement('span');
    count.className='unified-edit-weapon-count';
    count.textContent='×'+String(qty);
    row.append(name,count);
    fragment.appendChild(row);
  }});
  return cursor;
}}

'''
view_np = view_np.replace(render_marker, weapon_helpers + render_marker, 1)

old_unit_render = '''    const f=document.createDocumentFragment();
    const row=addUnifiedEditUnit(f,data,rowIndex);
    row.style.gridRow=String(cursor++);
    grid.appendChild(f);'''
new_unit_render = '''    const f=document.createDocumentFragment();
    const row=addUnifiedEditUnit(f,data,rowIndex);
    row.style.gridRow=String(cursor++);
    cursor=addBoyzUnifiedEditWeaponRows(f,data,rowIndex,cursor);
    grid.appendChild(f);'''
if view_np.count(old_unit_render) != 1:
    raise SystemExit(f'Unified Edit Unit-row render path: expected 1 match, found {view_np.count(old_unit_render)}')
view_np = view_np.replace(old_unit_render, new_unit_render, 1)

# Weapon rows extend the unified Edit sheet, so keep the existing dynamic iframe
# height synchronized after the rows are placed.
old_return = "  if(titlePoints)titlePoints.textContent='- '+String(sheetPoints)+' pts';\n  return rows.some(row=>row&&row.kind==='unit');"
new_return = "  if(titlePoints)titlePoints.textContent='- '+String(sheetPoints)+' pts';\n  if(typeof syncNewViewFrameHeight==='function')requestAnimationFrame(syncNewViewFrameHeight);\n  return rows.some(row=>row&&row.kind==='unit');"
if view_np.count(old_return) != 1:
    raise SystemExit(f'Unified Edit render return: expected 1 match, found {view_np.count(old_return)}')
view_np = view_np.replace(old_return, new_return, 1)

text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.110
    Scope: First Boyz weapon-parity pass in unified EDIT: render a flat Boyz weapon list with display counts sourced directly from data/orks/Weapon_Quantities.csv. The selected x10/x20 point option determines each displayed quantity, and the existing point-option refresh immediately re-renders the counts after a size change. Weapon order and names come from Unit_Weapons.csv and Weapon_Stats.csv. This pass intentionally does not add Boyz/Specials/Nob section grouping, Nob weapon-choice controls, compatibility rules, or loadout mutations.
    Risk areas: Unified EDIT Boyz flat weapon/count presentation and Edit sheet height only. VIEW, other Units, point-option mutation logic, weapon sections, loadouts, Old Edit, Cards, lock behavior, Version controls, persistence, Waha routing, and Probable remain unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.109\n'
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
    'const BOYZ_UNIFIED_EDIT_WEAPONS=',
    'function addBoyzUnifiedEditWeaponRows(fragment,data,rowIndex,cursor)',
    "return unitId==='BOYZ'||name==='BOYZ';",
    "return label==='x20'?'x20':label==='x10'?'x10':'';",
    "count.textContent='×'+String(qty);",
    'cursor=addBoyzUnifiedEditWeaponRows(f,data,rowIndex,cursor);',
    '.unified-edit-weapon-row{grid-column:1/span 16;',
    '.unified-edit-weapon-count{flex:0 0 auto;margin-left:6px;color:var(--orange);',
    "if(typeof syncNewViewFrameHeight==='function')requestAnimationFrame(syncNewViewFrameHeight);",
    'function ensurePersistentGridCells()',
    'function renderUnifiedEditRows(rows)',
]:
    if required not in final_view:
        raise SystemExit('V31.110 unified Edit acceptance failed: ' + required)

for forbidden in ['Weapon_Sections.csv', 'Loadout_Compatibility.csv', 'Loadout_Options.csv']:
    if forbidden in weapon_helpers:
        raise SystemExit('V31.110 scope regression: ' + forbidden)

for required in [
    '<title>WH40k 11th V31.110</title>',
    'The current baseline is WH40k_11th_V31.110;',
    'const APP_VERSION = "31.110";',
    "version: 'V31.110',",
    'CHANGE NOTE - WH40k_11th_V31.110',
]:
    if required not in text:
        raise SystemExit('V31.110 outer acceptance failed: ' + required)

# Protect the unified-page contract.
for forbidden in ['id="newEditPageScreen"', 'id="npEditFrame"', 'parent.getNewEdit']:
    if forbidden in text:
        raise SystemExit('V31.110 regressed retired standalone New Edit: ' + forbidden)

path.write_text(text, encoding='utf-8')
print(f'Built V31.110: Boyz weapon counts from Weapon_Quantities.csv ({len(boyz_weapons)} weapon profiles)')
