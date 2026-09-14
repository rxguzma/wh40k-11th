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
replace_once("<title>WH40k 11th V31.132</title>", "<title>WH40k 11th V31.133</title>", "title")
replace_once(
    "The current baseline is WH40k_11th_V31.132;",
    "The current baseline is WH40k_11th_V31.133;",
    "baseline",
)
replace_once('const APP_VERSION = "31.132";', 'const APP_VERSION = "31.133";', "APP_VERSION")
replace_once("version: 'V31.132',", "version: 'V31.133',", "quality version")

view_pat = re.compile(
    r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)',
    re.S,
)
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing")
view_np = html.unescape(vm.group(2))

for required in [
    "/* V31.129 compact Unit Ability buttons in unified New View. */",
    "const openAbilityKeys=new Set();",
    "function newViewAbilityIsOpen(key){",
    "function renderNewViewAbilitiesAndReflow(){",
    "let viewWeaponLayoutSyncDepth=0;",
    "function applyViewWeaponTagFocus(){",
]:
    if required not in view_np:
        raise SystemExit("V31.133 baseline contract missing: " + required)

# ---------------------------------------------------------------------------
# Ability geometry: each Ability is one full-width outer grid item. The title
# remains A-E and exactly two standard rows tall. When open, the detail appears
# beside it in F-P: Short Description first, then structured Tags immediately
# below. The right side grows naturally while the title stays at the top-left.
# ---------------------------------------------------------------------------
css_start = view_np.find("/* V31.129 compact Unit Ability buttons in unified New View. */")
css_end_marker = ".unit-ability-tags.ability-active .weapon-tag{opacity:1}"
css_end = view_np.find(css_end_marker, css_start)
if css_start < 0 or css_end < 0:
    raise SystemExit("Ability CSS bounds missing")
css_end += len(css_end_marker)
new_css = r'''/* V31.133 Unit Ability side-detail layout in unified New View. */
.unit-ability-block{grid-column:1/span 16;z-index:4;box-sizing:border-box;align-self:start;display:grid;grid-template-columns:repeat(16,var(--cell));align-items:start;min-width:0;min-height:calc(var(--cell)*2);background:transparent;overflow:visible}
.unit-ability-button{grid-column:1/span 5;grid-row:1;box-sizing:border-box;align-self:start;min-width:0;height:calc(var(--cell)*2);display:flex;align-items:center;justify-content:center;text-align:center;padding:4px 8px;white-space:normal;overflow:hidden;overflow-wrap:anywhere;background:var(--card);border:1px solid var(--border);border-radius:4px;color:rgba(241,243,244,.5);font:900 var(--body)/1 Roboto,Arial,sans-serif;cursor:pointer}
.unit-ability-button.ability-active{color:#80d6a3!important}
.unit-ability-detail{grid-column:6/span 11;grid-row:1;box-sizing:border-box;align-self:start;min-width:0;display:flex;flex-direction:column;align-items:stretch;background:transparent;overflow:visible}
.unit-ability-description-row{box-sizing:border-box;width:100%;min-width:0;min-height:calc(var(--cell)*2);display:flex;align-items:center;padding:4px 8px;white-space:normal;overflow:visible;overflow-wrap:anywhere;background:var(--card);border:1px solid var(--border);border-radius:4px;color:var(--secondary);font:700 var(--meta)/1.25 Roboto,Arial,sans-serif;cursor:pointer}
.unit-ability-tags{box-sizing:border-box;width:100%;min-width:0;min-height:var(--cell);display:flex;flex-wrap:wrap;align-items:center;align-content:center;justify-content:flex-start;gap:var(--gap);padding:1px 0;overflow:visible;background:transparent;cursor:pointer}
.unit-ability-tags .weapon-tag{height:auto;min-height:var(--std);max-width:100%;white-space:normal;overflow:visible;text-align:center;line-height:1.1;padding-top:4px;padding-bottom:4px}
.unit-ability-description-row.ability-active{color:#80d6a3!important}
.unit-ability-tags.ability-active .weapon-tag{opacity:1}'''
view_np = view_np[:css_start] + new_css + view_np[css_end:]

# Replace only the Ability helper block. Stop before the V31.131 Weapon Tag
# focus helpers so that behavior is preserved unchanged.
helper_start = view_np.find("function clearNewViewAbilityRows(){")
helper_end = view_np.find("let viewWeaponLayoutSyncDepth=0;", helper_start)
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
function newViewAbilityOpenToken(key){
  return String(activeUnitIndex)+'::'+String(key||'');
}
function newViewAbilityIsOpen(key){
  return openAbilityKeys.has(newViewAbilityOpenToken(key));
}
function selectNewViewAbility(key){
  const clean=String(key||'');
  const token=newViewAbilityOpenToken(clean);
  selectedWeaponIndex=null;
  if(openAbilityKeys.has(token)){
    openAbilityKeys.delete(token);
    if(String(selectedAbilityKey)===clean)selectedAbilityKey=null;
  }else{
    openAbilityKeys.add(token);
    selectedAbilityKey=clean;
  }
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
  block.className='unit-ability-block'+(active?' ability-expanded ability-active':'');
  block.dataset.abilityKey=String(key||'');
  block.style.gridColumn='1 / span 16';
  block.style.gridRow=String(startRow)+' / span 2';

  const button=document.createElement('div');
  button.className='unit-ability-button'+(active?' ability-active':'');
  button.textContent=String(ability&&ability.name||'');
  button.onclick=event=>{event.stopPropagation();selectNewViewAbility(key)};
  block.appendChild(button);

  let detail=null;
  if(active){
    detail=document.createElement('div');
    detail.className='unit-ability-detail';

    const description=document.createElement('div');
    description.className='unit-ability-description-row ability-active';
    description.textContent=String(ability&&ability.description||'');
    description.onclick=event=>{event.stopPropagation();selectNewViewAbility(key)};
    detail.appendChild(description);

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
      detail.appendChild(tags);
    }
    block.appendChild(detail);
  }

  grid.appendChild(block);
  if(!active)return 2;

  const cellPx=parseFloat(getComputedStyle(grid).getPropertyValue('--cell'))||26;
  const naturalHeight=Math.max(cellPx*2,block.scrollHeight||0,detail?detail.scrollHeight||0:0);
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

  // Retain exactly one empty standard grid row after the final visible Weapon.
  const abilityStartRow=weaponBottomRow+2;
  let cursor=abilityStartRow;
  abilities.forEach(ability=>{
    const key=String(ability&&ability.key||ability&&ability.abilityId||'');
    const active=Boolean(key&&newViewAbilityIsOpen(key));
    const visibleTags=newViewAbilityVisibleTags(ability).filter(tag=>String(tag&&tag.label||'').trim());
    const rowSpan=makeNewViewAbilityBlock(cursor,key,ability,visibleTags,active);
    cursor+=rowSpan;
  });

  const finalBottomRow=cursor-1;
  syncExpandedLayout(Math.max(1,finalBottomRow-detailStartRow+1));
  if(typeof syncNewViewFrameHeight==='function')syncNewViewFrameHeight();
  return Math.max(0,cursor-abilityStartRow);
}
'''
view_np = view_np[:helper_start] + new_helpers + "\n" + view_np[helper_end:]

text = text[: vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2) :]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.133
    Scope: Move unified New View Ability details beside their title buttons. Each Ability now occupies one full-width outer grid block: the Ability title remains A-E and two standard rows tall; when that Ability is open, its Short Description appears beside the title in F-P and its structured Tags appear immediately below the Description in the same F-P area. The right-side Description/Tag stack grows vertically as needed while the title remains anchored at the top-left. Abilities are stacked vertically so expanded side detail cannot overlap another Ability. The existing one-row gap after Weapons, standard muted title typography, independent per-Ability persistent open/close state, V31.131 Weapon Tag focus, lighter muted-Tag Unit separators, Ability filtering/data authority, and all other New View behavior remain unchanged.
    Risk areas: Unified New View Ability geometry/reflow only. No Ability data/order/filter semantics, Old Edit authority, Weapon/Boyz data, Unit stats, Probable, lock/FIX, Cards, Waha, CSV data, persistence, or Version controls changed.
  -->

'''
marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.132\n"
if text.count(marker) != 1:
    raise SystemExit("V31.132 change-note insertion marker missing")
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

# Focused acceptance checks.
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing after writeback")
final_view = html.unescape(vm.group(2))
for expected in [
    "/* V31.133 Unit Ability side-detail layout in unified New View. */",
    ".unit-ability-block{grid-column:1/span 16;",
    ".unit-ability-button{grid-column:1/span 5;grid-row:1;",
    ".unit-ability-detail{grid-column:6/span 11;grid-row:1;",
    "height:calc(var(--cell)*2);",
    "const openAbilityKeys=new Set();",
    "function newViewAbilityIsOpen(key){",
    "block.style.gridColumn='1 / span 16';",
    "detail.className='unit-ability-detail';",
    "detail.appendChild(description);",
    "detail.appendChild(tags);",
    "const abilityStartRow=weaponBottomRow+2;",
    "const active=Boolean(key&&newViewAbilityIsOpen(key));",
    "const rowSpan=makeNewViewAbilityBlock(cursor,key,ability,visibleTags,active);",
    "cursor+=rowSpan;",
    "let viewWeaponLayoutSyncDepth=0;",
    "function applyViewWeaponTagFocus(){",
    "background:rgba(154,160,166,.5);border:1px solid var(--border);",
]:
    if expected not in final_view:
        raise SystemExit("V31.133 View acceptance failed: " + expected)

for forbidden in [
    "grid-template-columns:repeat(4,var(--cell))",
    "for(let i=0;i<abilities.length;i+=4){",
    "const laneStart=1+(slot*4);",
    ".unit-ability-description-row{grid-column:1/span 4;grid-row:3;",
    ".unit-ability-tags{grid-column:1/span 4;grid-row:4;",
]:
    if forbidden in final_view:
        raise SystemExit("V31.133 acceptance failed: previous below-title Ability geometry remains: " + forbidden)

for expected in [
    "<title>WH40k 11th V31.133</title>",
    "The current baseline is WH40k_11th_V31.133;",
    'const APP_VERSION = "31.133";',
    "version: 'V31.133',",
    "CHANGE NOTE - WH40k_11th_V31.133",
]:
    if expected not in text:
        raise SystemExit("V31.133 release acceptance failed: " + expected)

path.write_text(text, encoding="utf-8")
print("Built V31.133: Ability title A-E with Description and Tags beside it in F-P")
