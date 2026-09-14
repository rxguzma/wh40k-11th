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
replace_once("<title>WH40k 11th V31.128</title>", "<title>WH40k 11th V31.129</title>", "title")
replace_once(
    "The current baseline is WH40k_11th_V31.128;",
    "The current baseline is WH40k_11th_V31.129;",
    "baseline",
)
replace_once('const APP_VERSION = "31.128";', 'const APP_VERSION = "31.129";', "APP_VERSION")
replace_once("version: 'V31.128',", "version: 'V31.129',", "quality version")

view_pat = re.compile(
    r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)',
    re.S,
)
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


# Replace only the New View Ability presentation. Ability data continues to be
# supplied by the existing Old Edit authoritative bridge.
css_start = view_np.find("/* V31.127 content-driven Unit Ability layout in unified New View. */")
css_end_marker = ".unit-ability-tags.ability-active .weapon-tag{opacity:1}"
css_end = view_np.find(css_end_marker, css_start)
if css_start < 0 or css_end < 0:
    raise SystemExit("V31.127 Ability CSS bounds missing")
css_end += len(css_end_marker)
new_css = r'''/* V31.129 compact Unit Ability buttons in unified New View. */
.unit-ability-block{z-index:4;box-sizing:border-box;align-self:start;display:grid;grid-template-columns:repeat(5,var(--cell));grid-template-rows:repeat(2,var(--cell));align-content:start;min-width:0;background:transparent;overflow:visible}
.unit-ability-block.ability-expanded{grid-template-rows:repeat(2,var(--cell)) minmax(calc(var(--cell)*2),auto) minmax(var(--cell),auto)}
.unit-ability-button{grid-column:1/span 5;grid-row:1/span 2;box-sizing:border-box;min-width:0;min-height:calc(var(--cell)*2);display:flex;align-items:center;justify-content:center;text-align:center;padding:4px 8px;white-space:normal;overflow:hidden;overflow-wrap:anywhere;background:var(--card);border:1px solid var(--border);border-radius:4px;color:var(--text);font:900 var(--body)/1.05 Roboto,Arial,sans-serif;cursor:pointer}
.unit-ability-button.ability-active{color:#80d6a3!important}
.unit-ability-description-row{grid-column:1/span 5;grid-row:3;box-sizing:border-box;min-width:0;min-height:calc(var(--cell)*2);display:flex;align-items:center;padding:4px 8px;white-space:normal;overflow:visible;overflow-wrap:anywhere;background:var(--card);border:1px solid var(--border);border-radius:4px;color:var(--secondary);font:700 var(--meta)/1.25 Roboto,Arial,sans-serif;cursor:pointer}
.unit-ability-tags{grid-column:1/span 5;grid-row:4;box-sizing:border-box;min-width:0;min-height:var(--cell);display:flex;flex-wrap:wrap;align-items:center;align-content:center;justify-content:flex-start;gap:var(--gap);padding:1px 0;overflow:visible;background:transparent;cursor:pointer}
.unit-ability-tags .weapon-tag{height:auto;min-height:var(--std);max-width:100%;white-space:normal;overflow:visible;text-align:center;line-height:1.1;padding-top:4px;padding-bottom:4px}
.unit-ability-description-row.ability-active{color:#80d6a3!important}
.unit-ability-tags.ability-active .weapon-tag{opacity:1}'''
view_np = view_np[:css_start] + new_css + view_np[css_end:]

# Keep the current filtering and transient selection contract, but pack Ability
# buttons into five-column lanes. Each button is exactly two grid rows tall.
# One full grid row is deliberately left empty after the last visible Weapon.
# Only the selected Ability reveals its Short Description and structured Tags,
# directly below that button in the same five-column lane.
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
function makeNewViewAbilityBlock(startRow,laneStart,key,ability,visibleTags,active){
  const block=document.createElement('div');
  block.className='unit-ability-block'+(active?' ability-expanded ability-active':'');
  block.dataset.abilityKey=String(key||'');
  block.style.gridColumn=String(laneStart)+' / span 5';
  block.style.gridRow=String(startRow)+' / span 2';

  const button=document.createElement('div');
  button.className='unit-ability-button'+(active?' ability-active':'');
  button.textContent=String(ability&&ability.name||'');
  button.onclick=event=>{event.stopPropagation();selectNewViewAbility(key)};
  block.appendChild(button);

  if(active){
    const description=document.createElement('div');
    description.className='unit-ability-description-row ability-active';
    description.textContent=String(ability&&ability.description||'');
    description.onclick=event=>{event.stopPropagation();selectNewViewAbility(key)};
    block.appendChild(description);

    if(visibleTags.length){
      const tags=document.createElement('div');
      tags.className='unit-ability-tags ability-active';
      visibleTags.forEach(tag=>{
        const badge=document.createElement('span');
        badge.className='weapon-tag';
        badge.textContent=String(tag&&tag.label||'');
        tags.appendChild(badge);
      });
      tags.onclick=event=>{event.stopPropagation();selectNewViewAbility(key)};
      block.appendChild(tags);
    }
  }

  grid.appendChild(block);

  if(!active)return 2;
  const cellPx=parseFloat(getComputedStyle(grid).getPropertyValue('--cell'))||26;
  const naturalHeight=Math.max(cellPx*2,block.scrollHeight||0);
  const rowSpan=Math.max(2,Math.ceil(naturalHeight/cellPx));
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

  if(!abilities.length){
    syncExpandedLayout(Math.max(1,weaponBottomRow-detailStartRow+1));
    if(typeof syncNewViewFrameHeight==='function')syncNewViewFrameHeight();
    return 0;
  }

  // Exactly one empty grid row separates Weapons from the first Ability buttons.
  const abilityStartRow=weaponBottomRow+2;
  let cursor=abilityStartRow;
  for(let i=0;i<abilities.length;i+=3){
    const group=abilities.slice(i,i+3);
    let groupSpan=2;
    group.forEach((ability,slot)=>{
      const key=String(ability&&ability.key||ability&&ability.abilityId||'');
      const active=Boolean(key&&String(selectedAbilityKey)===key);
      const visibleTags=newViewAbilityVisibleTags(ability).filter(tag=>String(tag&&tag.label||'').trim());
      const laneStart=1+(slot*5);
      const rowSpan=makeNewViewAbilityBlock(cursor,laneStart,key,ability,visibleTags,active);
      groupSpan=Math.max(groupSpan,rowSpan);
    });
    cursor+=groupSpan;
  }

  const finalBottomRow=cursor-1;
  syncExpandedLayout(Math.max(1,finalBottomRow-detailStartRow+1));
  if(typeof syncNewViewFrameHeight==='function')syncNewViewFrameHeight();
  return Math.max(0,cursor-abilityStartRow);
}
'''
view_np = view_np[:helper_start] + new_helpers + "\n" + view_np[helper_end:]

text = text[: vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2) :]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.129
    Scope: Redesign unified New View Unit Abilities as compact selectable buttons while retaining Old Edit as the authoritative Ability source. After the final visible Weapon/Weapon Tag, reserve exactly one empty standard grid row. Ability names then render as standard New View buttons exactly five grid columns wide and two grid rows tall, packed three per row. An unselected Ability shows only its button. Selecting one Ability reveals that Ability's Short Description directly below its button in the same five-column lane, followed immediately by its currently visible structured Tags; description and Tag content may grow vertically as needed and later Ability rows move down to avoid overlap. Existing Ability ordering, orders 8/9 View hiding, Range/Melee/Other/All filtering and scope-specific Tags, transient single Ability selection, Old Edit data/state, New View focus spacing, fonts, colors, borders, lock/report behavior, and 16-column grid are retained.
    Risk areas: Unified New View Unit Ability presentation/reflow only. No Old Edit, CSV schema/data, Weapon data/layout, Unit stats, Probable mechanics, Cards, Waha, persistence, or Version-control behavior changes.
  -->

'''
marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.128\n"
if text.count(marker) != 1:
    raise SystemExit("V31.128 change-note insertion marker missing")
text = text.replace(marker, note + marker, 1)

# Keep only the five newest detailed V31 change notes.
notes = list(
    re.finditer(
        r"\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n",
        text,
        re.S,
    )
)
for match in reversed(notes[5:]):
    text = text[: match.start()] + text[match.end() :]

# Focused acceptance checks for the approved Ability button layout.
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing after writeback")
final_view = html.unescape(vm.group(2))
for expected in [
    "/* V31.129 compact Unit Ability buttons in unified New View. */",
    ".unit-ability-block{z-index:4;",
    "grid-template-columns:repeat(5,var(--cell))",
    ".unit-ability-button{grid-column:1/span 5;grid-row:1/span 2;",
    "block.style.gridColumn=String(laneStart)+' / span 5';",
    "block.style.gridRow=String(startRow)+' / span 2';",
    "if(!active)return 2;",
    "if(active){",
    "description.className='unit-ability-description-row ability-active';",
    "tags.className='unit-ability-tags ability-active';",
    "const abilityStartRow=weaponBottomRow+2;",
    "for(let i=0;i<abilities.length;i+=3){",
    "const laneStart=1+(slot*5);",
    "groupSpan=Math.max(groupSpan,rowSpan);",
]:
    if expected not in final_view:
        raise SystemExit("V31.129 View acceptance failed: " + expected)

for forbidden in [
    ".unit-ability-block{grid-column:1/span 16;",
    ".unit-ability-name-row{grid-column:1/span 6;",
    ".unit-ability-description-row{grid-column:7/span 10;",
]:
    if forbidden in final_view:
        raise SystemExit("V31.129 acceptance failed: old full-width Ability geometry remains: " + forbidden)

for expected in [
    "<title>WH40k 11th V31.129</title>",
    "The current baseline is WH40k_11th_V31.129;",
    'const APP_VERSION = "31.129";',
    "version: 'V31.129',",
    "CHANGE NOTE - WH40k_11th_V31.129",
]:
    if expected not in text:
        raise SystemExit("V31.129 release acceptance failed: " + expected)

path.write_text(text, encoding="utf-8")
print("Built V31.129: one-row Weapon gap, five-column two-row Ability buttons, selected detail and Tags below")
