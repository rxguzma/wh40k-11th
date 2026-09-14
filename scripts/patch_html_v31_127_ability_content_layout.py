from pathlib import Path
import html
import re

path = Path("WH40k_11th.html")
text = path.read_text(encoding="utf-8")


def replace_once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    text = text.replace(old, new, 1)


# Sequential release metadata.
replace_once("<title>WH40k 11th V31.126</title>", "<title>WH40k 11th V31.127</title>", "title")
replace_once("The current baseline is WH40k_11th_V31.126;", "The current baseline is WH40k_11th_V31.127;", "baseline")
replace_once('const APP_VERSION = "31.126";', 'const APP_VERSION = "31.127";', "APP_VERSION")
replace_once("version: 'V31.126',", "version: 'V31.127',", "quality version")

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing")
view_np = html.unescape(vm.group(2))


def view_replace_once(old, new, label):
    global view_np
    count = view_np.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    view_np = view_np.replace(old, new, 1)


# Replace the V31.125 fixed-grid Ability CSS with one atomic, content-driven
# Ability block. The visual tokens remain the existing New View design system.
css_start = view_np.find("/* V31.125 Unit Ability grid layout in unified New View. */")
css_end_marker = ".unit-ability-tags.ability-active .weapon-tag{opacity:1}"
css_end = view_np.find(css_end_marker, css_start)
if css_start < 0 or css_end < 0:
    raise SystemExit("V31.125 Ability CSS bounds missing")
css_end += len(css_end_marker)
new_css = r'''/* V31.127 content-driven Unit Ability layout in unified New View. */
.unit-ability-block{grid-column:1/span 16;z-index:4;box-sizing:border-box;align-self:start;display:grid;grid-template-columns:repeat(16,var(--cell));background:var(--card);cursor:pointer;overflow:visible}
.unit-ability-block.has-tags{grid-template-rows:minmax(calc(var(--cell)*2),auto) minmax(var(--cell),auto)}
.unit-ability-block:not(.has-tags){grid-template-rows:minmax(calc(var(--cell)*2),auto)}
.unit-ability-name-row{grid-column:1/span 6;grid-row:1/-1;box-sizing:border-box;min-width:0;display:flex;align-items:center;justify-content:center;text-align:center;padding:4px 8px;white-space:normal;overflow:visible;overflow-wrap:anywhere;background:var(--card);border-right:1px solid var(--border);border-bottom:1px solid var(--border);color:var(--text);font:900 var(--body)/1 Roboto,Arial,sans-serif}
.unit-ability-description-row{grid-column:7/span 10;grid-row:1;box-sizing:border-box;min-width:0;min-height:calc(var(--cell)*2);display:flex;align-items:center;padding:4px 8px;white-space:normal;overflow:visible;overflow-wrap:anywhere;background:var(--card);border-bottom:1px solid var(--border);color:var(--secondary);font:700 var(--meta)/1.25 Roboto,Arial,sans-serif}
.unit-ability-tags{grid-column:7/span 10;grid-row:2;box-sizing:border-box;min-width:0;min-height:var(--cell);display:flex;flex-wrap:wrap;align-items:center;align-content:center;justify-content:flex-start;gap:var(--gap);padding:1px 0;overflow:visible;background:var(--card);border-bottom:1px solid var(--border)}
.unit-ability-tags .weapon-tag{height:auto;min-height:var(--std);max-width:100%;white-space:normal;overflow:visible;text-align:center;line-height:1.1;padding-top:4px;padding-bottom:4px}
.unit-ability-name-row.ability-muted,.unit-ability-description-row.ability-muted{color:rgba(241,243,244,.5)!important}
.unit-ability-tags.ability-muted .weapon-tag{color:rgba(154,160,166,.5)!important}
.unit-ability-name-row.ability-active,.unit-ability-description-row.ability-active{color:#80d6a3!important}
.unit-ability-tags.ability-active .weapon-tag{opacity:1}'''
view_np = view_np[:css_start] + new_css + view_np[css_end:]

# Replace only the Ability render/reflow helper block. Each Ability is one
# top-level grid item; its internal Description and Tags grow naturally, then
# the outer grid reserves the matching number of standard New View row sizes.
helper_start = view_np.find("function clearNewViewAbilityRows(){")
helper_end = view_np.find("function syncViewSelectionPresentation(){", helper_start)
if helper_start < 0 or helper_end < 0:
    raise SystemExit("Ability helper bounds missing")

new_helpers = r'''function clearNewViewAbilityRows(){
  grid.querySelectorAll('.unit-ability-block').forEach(el=>el.remove());
}
function newViewAbilityFilterScope(scope){
  const clean=String(scope||'all').toLowerCase();
  if(clean==='range'||clean==='ranged')return 'SHOOT';
  if(clean==='melee')return 'MELEE';
  return 'OTHER';
}
function newViewAbilityMatchesFilter(ability){
  if(weaponFilterMode==='ALL')return true;
  const tags=Array.isArray(ability&&ability.tags)?ability.tags:[];
  const scoped=new Set(tags.map(tag=>newViewAbilityFilterScope(tag&&tag.scope)).filter(scope=>scope!=='OTHER'));
  if(weaponFilterMode==='OTHER')return scoped.size===0;
  return scoped.has(weaponFilterMode);
}
function newViewAbilityVisibleTags(ability){
  const tags=Array.isArray(ability&&ability.tags)?ability.tags:[];
  if(weaponFilterMode==='ALL'||weaponFilterMode==='OTHER')return tags;
  return tags.filter(tag=>newViewAbilityFilterScope(tag&&tag.scope)===weaponFilterMode);
}
function selectNewViewAbility(key){
  const clean=String(key||'');
  selectedWeaponIndex=null;
  selectedAbilityKey=selectedAbilityKey===clean?null:clean;
  syncWeaponLayout();
}
function newViewLastVisibleWeaponRow(detailStartRow){
  let bottom=detailStartRow;
  grid.querySelectorAll('.weapon-header,.weapon-row,.weapon-tags,.boyz-subunit-node').forEach(el=>{
    if(!viewPresentationVisible(el))return;
    const row=parseInt(el.style.gridRow||getComputedStyle(el).gridRowStart,10);
    if(!Number.isFinite(row))return;
    const spanMatch=String(el.style.gridRow||'').match(/span\s+(\d+)/i);
    const span=spanMatch?Math.max(1,Number(spanMatch[1])||1):1;
    bottom=Math.max(bottom,row+span-1);
  });
  return bottom;
}
function makeNewViewAbilityBlock(startRow,key,ability,visibleTags,active){
  const block=document.createElement('div');
  block.className='unit-ability-block '+(visibleTags.length?'has-tags ':'')+(active?'ability-active':'ability-muted');
  block.dataset.abilityKey=String(key||'');
  block.style.gridRow=String(startRow);

  const name=document.createElement('div');
  name.className='unit-ability-name-row '+(active?'ability-active':'ability-muted');
  name.textContent=String(ability&&ability.name||'');
  block.appendChild(name);

  const description=document.createElement('div');
  description.className='unit-ability-description-row '+(active?'ability-active':'ability-muted');
  description.textContent=String(ability&&ability.description||'');
  block.appendChild(description);

  let tags=null;
  if(visibleTags.length){
    tags=document.createElement('div');
    tags.className='unit-ability-tags '+(active?'ability-active':'ability-muted');
    visibleTags.forEach(tag=>{
      const badge=document.createElement('span');
      badge.className='weapon-tag';
      badge.textContent=String(tag&&tag.label||'');
      tags.appendChild(badge);
    });
    block.appendChild(tags);
  }

  block.onclick=event=>{event.stopPropagation();selectNewViewAbility(key)};
  grid.appendChild(block);

  const cellPx=parseFloat(getComputedStyle(grid).getPropertyValue('--cell'))||26;
  const minRows=visibleTags.length?3:2;
  const naturalHeight=Math.max(
    block.scrollHeight,
    description.scrollHeight+(tags?tags.scrollHeight:0),
    name.scrollHeight,
    cellPx*minRows
  );
  const rowSpan=Math.max(minRows,Math.ceil(naturalHeight/cellPx));
  block.style.gridRow=String(startRow)+' / span '+String(rowSpan);
  block.style.alignSelf='stretch';
  return rowSpan;
}
function renderNewViewAbilitiesAndReflow(){
  clearNewViewAbilityRows();
  if(activePageMode!=='view'||activeUnitIndex===null)return 0;
  const data=unitDataByIndex[activeUnitIndex];
  if(!data)return 0;
  const activeRow=unitRow(activeUnitIndex);
  const activeGridRow=activeRow?parseInt(activeRow.style.gridRow||getComputedStyle(activeRow).gridRowStart,10):NaN;
  if(!Number.isFinite(activeGridRow))return 0;

  const detailStartRow=activeGridRow+1;
  const weaponBottomRow=newViewLastVisibleWeaponRow(detailStartRow);
  const abilities=(Array.isArray(data.abilities)?data.abilities:[]).filter(newViewAbilityMatchesFilter);
  if(selectedAbilityKey&&!abilities.some(ability=>String(ability&&ability.key||'')===String(selectedAbilityKey)))selectedAbilityKey=null;

  let cursor=weaponBottomRow+1;
  const firstAbilityRow=cursor;
  abilities.forEach(ability=>{
    const key=String(ability&&ability.key||ability&&ability.abilityId||'');
    const active=Boolean(key&&String(selectedAbilityKey)===key);
    const visibleTags=newViewAbilityVisibleTags(ability).filter(tag=>String(tag&&tag.label||'').trim());
    const rowSpan=makeNewViewAbilityBlock(cursor,key,ability,visibleTags,active);
    cursor+=rowSpan;
  });

  const finalBottomRow=abilities.length?cursor-1:weaponBottomRow;
  syncExpandedLayout(Math.max(1,finalBottomRow-detailStartRow+1));
  if(typeof syncNewViewFrameHeight==='function')syncNewViewFrameHeight();
  return Math.max(0,cursor-firstAbilityRow);
}
'''
view_np = view_np[:helper_start] + new_helpers + "\n" + view_np[helper_end:]

# V31.126 focus-row logic must treat each Ability as one atomic item. Preserve
# row spans when it shifts the opened Unit content down by one focus row.
old_focus_selector = ".unit-ability-name-row,.unit-ability-description-row,.unit-ability-tags,.weapon-row,.weapon-tags,.boyz-subunit-node"
new_focus_selector = ".unit-ability-block,.weapon-row,.weapon-tags,.boyz-subunit-node"
selector_count = view_np.count(old_focus_selector)
if selector_count != 2:
    raise SystemExit(f"focus selector: expected 2 matches, found {selector_count}")
view_np = view_np.replace(old_focus_selector, new_focus_selector)

old_shift = """  el.style.gridRow=String(row+delta);\n  return true;\n}"""
new_shift = """  const spanMatch=String(el.style.gridRow||'').match(/span\\s+(\\d+)/i);\n  const span=spanMatch?Math.max(1,Number(spanMatch[1])||1):1;\n  el.style.gridRow=String(row+delta)+(span>1?' / span '+String(span):'');\n  return true;\n}"""
view_replace_once(old_shift, new_shift, "focus row span preservation")

old_bottom = """  contentNodes.forEach(el=>{\n    const row=viewGridRowNumber(el);\n    if(Number.isFinite(row))bottomRow=Math.max(bottomRow,row);\n  });"""
new_bottom = """  contentNodes.forEach(el=>{\n    const row=viewGridRowNumber(el);\n    if(!Number.isFinite(row))return;\n    const spanMatch=String(el.style.gridRow||'').match(/span\\s+(\\d+)/i);\n    const span=spanMatch?Math.max(1,Number(spanMatch[1])||1):1;\n    bottomRow=Math.max(bottomRow,row+span-1);\n  });"""
view_replace_once(old_bottom, new_bottom, "focus bottom row span")

text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.127
    Scope: Correct unified New View Unit Ability geometry. Each Ability is now one atomic content-driven block after Weapons: A-F is one centered Ability Name box spanning the full Ability height; G-P contains the Short Description above its structured Tags. Description text wraps and grows vertically as needed. Tags retain the existing Weapon Tag visual format, wrap as needed, and can grow vertically. The Ability Name grows with the combined Description/Tags height. The outer New View grid reserves the matching number of standard row-size units, eliminating clipped text, oversized implicit rows, and blank gaps between Abilities. Existing Old Edit authoritative Ability data/order, orders 8/9 visibility rule, Range/Melee/Other/All filtering, transient selection, V31.126 focus-row behavior, fonts, colors, borders, and grid dimensions are retained.
    Risk areas: Unified New View Unit Ability layout/reflow and opened-Unit focus bounds only. No Old Edit, CSV schema/data, Weapon data/layout, Unit stats, Probable mechanics, Cards, Waha, persistence, lock behavior, or report storage changes.
  -->

'''
marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.126\n"
if marker not in text:
    raise SystemExit("V31.126 change-note insertion marker missing")
text = text.replace(marker, note + marker, 1)

notes = list(re.finditer(r"\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n", text, re.S))
for match in reversed(notes[5:]):
    text = text[:match.start()] + text[match.end():]

# Focused acceptance checks for the approved Ability format.
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified View missing after writeback")
final_view = html.unescape(vm.group(2))
checks = [
    "/* V31.127 content-driven Unit Ability layout in unified New View. */",
    ".unit-ability-block{grid-column:1/span 16;",
    ".unit-ability-name-row{grid-column:1/span 6;grid-row:1/-1;",
    ".unit-ability-description-row{grid-column:7/span 10;grid-row:1;",
    ".unit-ability-tags{grid-column:7/span 10;grid-row:2;",
    "flex-wrap:wrap",
    ".unit-ability-tags .weapon-tag{height:auto;min-height:var(--std);max-width:100%;white-space:normal;",
    "const minRows=visibleTags.length?3:2;",
    "const rowSpan=Math.max(minRows,Math.ceil(naturalHeight/cellPx));",
    "block.style.gridRow=String(startRow)+' / span '+String(rowSpan);",
    "let cursor=weaponBottomRow+1;",
    "cursor+=rowSpan;",
    "grid.querySelectorAll('.unit-ability-block,.weapon-row,.weapon-tags,.boyz-subunit-node')",
]
for expected in checks:
    if expected not in final_view:
        raise SystemExit("V31.127 acceptance failed: " + expected)

if ".unit-ability-description-row{grid-column:7/span 10;z-index:4" in final_view:
    raise SystemExit("V31.127 acceptance failed: old fixed Ability CSS still present")
if "makeNewViewAbilityCell('unit-ability-name-row'" in final_view:
    raise SystemExit("V31.127 acceptance failed: old split-cell renderer still present")

for expected in [
    "<title>WH40k 11th V31.127</title>",
    "The current baseline is WH40k_11th_V31.127;",
    'const APP_VERSION = "31.127";',
    "version: 'V31.127',",
    "CHANGE NOTE - WH40k_11th_V31.127",
]:
    if expected not in text:
        raise SystemExit("V31.127 release acceptance failed: " + expected)

path.write_text(text, encoding="utf-8")
print("Built V31.127: content-driven Ability Name | Description/Tags layout after Weapons")
