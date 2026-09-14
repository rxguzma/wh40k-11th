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
once('<title>WH40k 11th V31.117</title>', '<title>WH40k 11th V31.118</title>', 'title')
once('The current baseline is WH40k_11th_V31.117;', 'The current baseline is WH40k_11th_V31.118;', 'baseline')
once('const APP_VERSION = "31.117";', 'const APP_VERSION = "31.118";', 'APP_VERSION')
once("version: 'V31.117',", "version: 'V31.118',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing')
view_np = html.unescape(vm.group(2))

# Track the most recently opened Boyz sub-unit so the other visible headers can
# reuse the existing weapon-muted treatment without introducing new colors.
old_state = "const boyzNewViewSubunitOpen={Boyz:false,Specials:false,Nob:false};\nlet boyzNewViewSelectedWeaponId='';"
new_state = "const boyzNewViewSubunitOpen={Boyz:false,Specials:false,Nob:false};\nlet boyzNewViewActiveSubunit='';\nlet boyzNewViewSelectedWeaponId='';"
if view_np.count(old_state) != 1:
    raise SystemExit(f'Boyz sub-unit state anchor: expected 1 match, found {view_np.count(old_state)}')
view_np = view_np.replace(old_state, new_state, 1)

old_header = r'''function makeBoyzSubunitHeader(template,label){
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
new_header = r'''function makeBoyzSubunitHeader(template,label,muted=false){
  const row=template.cloneNode(true);
  row.classList.add('boyz-subunit-node','boyz-subunit-header');
  row.classList.toggle('weapon-muted',Boolean(muted));
  row.style.display='grid';
  const name=row.querySelector('.weapon-name');
  if(name)name.textContent=label;
  const open=Boolean(boyzNewViewSubunitOpen[label]);
  [...row.children].forEach(cell=>{if(cell!==name)cell.style.visibility=open?'visible':'hidden'});
  row.onclick=e=>{
    e.stopPropagation();
    const nextOpen=!boyzNewViewSubunitOpen[label];
    boyzNewViewSubunitOpen[label]=nextOpen;
    if(nextOpen)boyzNewViewActiveSubunit=label;
    else if(boyzNewViewActiveSubunit===label){
      const fallback=BOYZ_NEW_VIEW_SUBUNITS.find(def=>boyzNewViewSubunitOpen[def.label]);
      boyzNewViewActiveSubunit=fallback?fallback.label:'';
    }
    renderBoyzNewViewSubunits(unitDataByIndex[activeUnitIndex]);
  };
  return row;
}'''
if view_np.count(old_header) != 1:
    raise SystemExit(f'Boyz sub-unit header renderer: expected 1 match, found {view_np.count(old_header)}')
view_np = view_np.replace(old_header, new_header, 1)

old_loop = r'''  const nodes=[];
  BOYZ_NEW_VIEW_SUBUNITS.forEach(def=>{
    nodes.push(makeBoyzSubunitHeader(baseHeader,def.label));
    if(!boyzNewViewSubunitOpen[def.label])return;
    const orderedIds=def.weaponIds.slice();
    const selected=normalizeBoyzWeaponId(boyzNewViewSelectedWeaponId);
    const selectedIndex=orderedIds.findIndex(id=>normalizeBoyzWeaponId(id)===selected);
    if(selectedIndex>0){
      const selectedId=orderedIds.splice(selectedIndex,1)[0];
      orderedIds.unshift(selectedId);
    }
    orderedIds.forEach(id=>{
      const weapon=byId.get(id);
      if(!weapon||!boyzWeaponPassesFilter(weapon))return;
      nodes.push(makeBoyzWeaponRow(baseWeapon,weapon));
      const tagRow=makeBoyzWeaponTags(baseTags,weapon);
      if(tagRow)nodes.push(tagRow);
    });
  });'''
new_loop = r'''  const nodes=[];
  const visibleDefs=BOYZ_NEW_VIEW_SUBUNITS.map(def=>{
    const weaponIds=def.weaponIds.filter(id=>{
      const weapon=byId.get(id);
      return Boolean(weapon)&&boyzWeaponPassesFilter(weapon);
    });
    if(!weaponIds.length)boyzNewViewSubunitOpen[def.label]=false;
    return {def,weaponIds};
  }).filter(item=>item.weaponIds.length);
  const visibleLabels=new Set(visibleDefs.map(item=>item.def.label));
  if(!visibleLabels.has(boyzNewViewActiveSubunit)){
    const fallback=visibleDefs.find(item=>boyzNewViewSubunitOpen[item.def.label]);
    boyzNewViewActiveSubunit=fallback?fallback.def.label:'';
  }
  visibleDefs.forEach(({def,weaponIds})=>{
    const muted=Boolean(boyzNewViewActiveSubunit)&&boyzNewViewActiveSubunit!==def.label;
    nodes.push(makeBoyzSubunitHeader(baseHeader,def.label,muted));
    if(!boyzNewViewSubunitOpen[def.label])return;
    const orderedIds=weaponIds.slice();
    const selected=normalizeBoyzWeaponId(boyzNewViewSelectedWeaponId);
    const selectedIndex=orderedIds.findIndex(id=>normalizeBoyzWeaponId(id)===selected);
    if(selectedIndex>0){
      const selectedId=orderedIds.splice(selectedIndex,1)[0];
      orderedIds.unshift(selectedId);
    }
    orderedIds.forEach(id=>{
      const weapon=byId.get(id);
      if(!weapon)return;
      nodes.push(makeBoyzWeaponRow(baseWeapon,weapon));
      const tagRow=makeBoyzWeaponTags(baseTags,weapon);
      if(tagRow)nodes.push(tagRow);
    });
  });'''
if view_np.count(old_loop) != 1:
    raise SystemExit(f'Boyz sub-unit render loop: expected 1 match, found {view_np.count(old_loop)}')
view_np = view_np.replace(old_loop, new_loop, 1)

text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.118
    Scope: Refine Boyz New View sub-units only. A Boyz / Specials / Nob sub-unit header now disappears completely when the current Range / Melee / Other / All filter leaves that sub-unit with no visible weapons. When a visible sub-unit is opened, the other visible sub-unit headers reuse the existing weapon-muted gray treatment; closing the focused sub-unit restores the next open sub-unit as focus, or normal header treatment when none remain open. Existing weapon rows, tags, selected-weapon top ordering, quantities, header stat-label behavior, grid sizing, fonts, and colors are otherwise unchanged.
    Risk areas: Boyz New View sub-unit visibility and header focus treatment only. Other Units, weapon data, filters, Unit Detail, lock/frozen behavior, unified Edit, FIX reports, Version controls, Cards, persistence, CSV data, Waha routing, and Probable remain unchanged.
  -->

'''
marker = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.117\n'
if text.count(marker) != 1:
    raise SystemExit('V31.117 change-note insertion marker missing')
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
    "let boyzNewViewActiveSubunit='';",
    "function makeBoyzSubunitHeader(template,label,muted=false)",
    "row.classList.toggle('weapon-muted',Boolean(muted));",
    "if(nextOpen)boyzNewViewActiveSubunit=label;",
    "const visibleDefs=BOYZ_NEW_VIEW_SUBUNITS.map(def=>{",
    "return Boolean(weapon)&&boyzWeaponPassesFilter(weapon);",
    "if(!weaponIds.length)boyzNewViewSubunitOpen[def.label]=false;",
    ").filter(item=>item.weaponIds.length);",
    "const muted=Boolean(boyzNewViewActiveSubunit)&&boyzNewViewActiveSubunit!==def.label;",
    "nodes.push(makeBoyzSubunitHeader(baseHeader,def.label,muted));",
    "const orderedIds=weaponIds.slice();",
]:
    if expected not in final_view:
        raise SystemExit('V31.118 Boyz sub-unit acceptance failed: ' + expected)

for expected in [
    '<title>WH40k 11th V31.118</title>',
    'The current baseline is WH40k_11th_V31.118;',
    'const APP_VERSION = "31.118";',
    "version: 'V31.118',",
    'CHANGE NOTE - WH40k_11th_V31.118',
]:
    if expected not in text:
        raise SystemExit('V31.118 release acceptance failed: ' + expected)

path.write_text(text, encoding='utf-8')
print('Built V31.118: Boyz sub-unit filter visibility and focus muting')
