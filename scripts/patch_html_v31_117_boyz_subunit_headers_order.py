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
once('<title>WH40k 11th V31.116</title>', '<title>WH40k 11th V31.117</title>', 'title')
once('The current baseline is WH40k_11th_V31.116;', 'The current baseline is WH40k_11th_V31.117;', 'baseline')
once('const APP_VERSION = "31.116";', 'const APP_VERSION = "31.117";', 'APP_VERSION')
once("version: 'V31.116',", "version: 'V31.117',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing')
view_np = html.unescape(vm.group(2))

old_header = r'''function makeBoyzSubunitHeader(template,label){
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
}'''
new_header = r'''function makeBoyzSubunitHeader(template,label){
  const row=template.cloneNode(true);
  row.classList.add('boyz-subunit-node','boyz-subunit-header');
  row.style.display='grid';
  const name=row.querySelector('.weapon-name');
  if(name)name.textContent=label;
  const open=Boolean(boyzNewViewSubunitOpen[label]);
  [...row.children].forEach(cell=>{if(cell!==name)cell.style.visibility=open?'visible':'hidden'});
  row.onclick=e=>{
    e.stopPropagation();
    boyzNewViewSubunitOpen[label]=!boyzNewViewSubunitOpen[label];
    renderBoyzNewViewSubunits(unitDataByIndex[activeUnitIndex]);
  };
  return row;
}'''
if view_np.count(old_header) != 1:
    raise SystemExit(f'Boyz sub-unit header renderer: expected 1 match, found {view_np.count(old_header)}')
view_np = view_np.replace(old_header, new_header, 1)

old_select = r'''  row.onclick=e=>{
    e.stopPropagation();
    const id=String(row.dataset.weaponId||'');
    boyzNewViewSelectedWeaponId=normalizeBoyzWeaponId(boyzNewViewSelectedWeaponId)===normalizeBoyzWeaponId(id)?'':id;
    refreshBoyzNewViewSelection();
  };'''
new_select = r'''  row.onclick=e=>{
    e.stopPropagation();
    const id=String(row.dataset.weaponId||'');
    boyzNewViewSelectedWeaponId=normalizeBoyzWeaponId(boyzNewViewSelectedWeaponId)===normalizeBoyzWeaponId(id)?'':id;
    renderBoyzNewViewSubunits(unitDataByIndex[activeUnitIndex]);
  };'''
if view_np.count(old_select) != 1:
    raise SystemExit(f'Boyz weapon selection handler: expected 1 match, found {view_np.count(old_select)}')
view_np = view_np.replace(old_select, new_select, 1)

old_order = r'''    def.weaponIds.forEach(id=>{
      const weapon=byId.get(id);'''
new_order = r'''    const orderedIds=def.weaponIds.slice();
    const selected=normalizeBoyzWeaponId(boyzNewViewSelectedWeaponId);
    const selectedIndex=orderedIds.findIndex(id=>normalizeBoyzWeaponId(id)===selected);
    if(selectedIndex>0){
      const selectedId=orderedIds.splice(selectedIndex,1)[0];
      orderedIds.unshift(selectedId);
    }
    orderedIds.forEach(id=>{
      const weapon=byId.get(id);'''
if view_np.count(old_order) != 1:
    raise SystemExit(f'Boyz sub-unit weapon order loop: expected 1 match, found {view_np.count(old_order)}')
view_np = view_np.replace(old_order, new_order, 1)

text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.117
    Scope: Refine Boyz New View sub-units only. Boyz / Specials / Nob headers now hide R\" / A / WS / St / AP / D while collapsed and show those existing labels only while that sub-unit is open. Selecting a weapon now re-renders its sub-unit with that weapon and its existing Tag row moved to the top, matching the established New View selected-weapon ordering; deselecting restores the approved canonical order. No arrows, counts, new colors, new borders, or new controls are added.
    Risk areas: Boyz expanded Weapon sub-unit header labels and selected-weapon ordering only. Other Units, weapon data, quantities, filters, Unit Detail, lock/frozen behavior, unified Edit, FIX reports, Version controls, Cards, persistence, CSV data, Waha routing, and Probable remain unchanged.
  -->

'''
marker = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.116\n'
if text.count(marker) != 1:
    raise SystemExit('V31.116 change-note insertion marker missing')
text = text.replace(marker, note + marker, 1)

# Keep only the five newest detailed V31 change notes.
notes = list(re.finditer(r'\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n', text, re.S))
for match in reversed(notes[5:]):
    text = text[:match.start()] + text[match.end():]

# Acceptance checks.
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing after writeback')
final_view = html.unescape(vm.group(2))
for expected in [
    "const open=Boolean(boyzNewViewSubunitOpen[label]);",
    "[...row.children].forEach(cell=>{if(cell!==name)cell.style.visibility=open?'visible':'hidden'});",
    "boyzNewViewSelectedWeaponId=normalizeBoyzWeaponId(boyzNewViewSelectedWeaponId)===normalizeBoyzWeaponId(id)?'':id;\n    renderBoyzNewViewSubunits(unitDataByIndex[activeUnitIndex]);",
    "const orderedIds=def.weaponIds.slice();",
    "const selectedIndex=orderedIds.findIndex(id=>normalizeBoyzWeaponId(id)===selected);",
    "orderedIds.unshift(selectedId);",
    "orderedIds.forEach(id=>{",
    "{label:'Boyz',weaponIds:['SLUGGA','SHOOTA','CHOPPA']}",
    "{label:'Specials',weaponIds:['BIG_SHOOTA','BURNA','ROKKIT_LAUNCHA_BLASTA','ROKKIT_LAUNCHA_BUSTA']}",
    "{label:'Nob',weaponIds:['KOMBI_SKORCHA_SHOOTA','KOMBI_SKORCHA_SKORCHA']}",
]:
    if expected not in final_view:
        raise SystemExit('V31.117 Boyz sub-unit acceptance failed: ' + expected)

for expected in [
    '<title>WH40k 11th V31.117</title>',
    'The current baseline is WH40k_11th_V31.117;',
    'const APP_VERSION = "31.117";',
    "version: 'V31.117',",
    'CHANGE NOTE - WH40k_11th_V31.117',
]:
    if expected not in text:
        raise SystemExit('V31.117 release acceptance failed: ' + expected)

path.write_text(text, encoding='utf-8')
print('Built V31.117: Boyz collapsed headers and selected-weapon ordering')
