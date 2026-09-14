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
replace_once("<title>WH40k 11th V31.134</title>", "<title>WH40k 11th V31.135</title>", "title")
replace_once(
    "The current baseline is WH40k_11th_V31.134;",
    "The current baseline is WH40k_11th_V31.135;",
    "baseline",
)
replace_once('const APP_VERSION = "31.134";', 'const APP_VERSION = "31.135";', "APP_VERSION")
replace_once("version: 'V31.134',", "version: 'V31.135',", "quality version")

# Old Edit remains authoritative. Add explicit short/long display projections so
# New View can toggle between them without guessing from rendered text.
old_projection = '                description: String(effectiveItem.shortText || effectiveItem.text || effectiveItem.longText || sourceItem.shortText || sourceItem.text || sourceItem.longText || ""),\n'
new_projection = '''                description: String(effectiveItem.shortText || effectiveItem.text || effectiveItem.longText || sourceItem.shortText || sourceItem.text || sourceItem.longText || ""),
                shortDescription: String(effectiveItem.shortText || sourceItem.shortText || effectiveItem.text || sourceItem.text || effectiveItem.longText || sourceItem.longText || ""),
                longDescription: String(effectiveItem.longText || sourceItem.longText || effectiveItem.text || sourceItem.text || effectiveItem.shortText || sourceItem.shortText || ""),
'''
replace_once(old_projection, new_projection, "Ability short/long projection")

view_pat = re.compile(
    r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)',
    re.S,
)
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing")
view_np = html.unescape(vm.group(2))

for required in [
    "/* V31.133 Unit Ability side-detail layout in unified New View. */",
    "/* V31.134 New View muted-gray presentation */",
    "let selectedAbilityKey=null;",
    "const openAbilityKeys=new Set();",
    "function newViewAbilityIsOpen(key){",
    "function renderNewViewAbilitiesAndReflow(){",
    "let viewWeaponLayoutSyncDepth=0;",
    "function applyViewWeaponTagFocus(){",
]:
    if required not in view_np:
        raise SystemExit("V31.135 baseline contract missing: " + required)

# Independent transient Ability states: title Active/Inactive and Short/Long
# description. These states do not own or clear Weapon selection.
old_state = "let selectedAbilityKey=null;\nconst openAbilityKeys=new Set();"
new_state = "let selectedAbilityKey=null;\nconst activeAbilityKeys=new Set();\nconst longAbilityDescriptionKeys=new Set();"
if view_np.count(old_state) != 1:
    raise SystemExit(f"Ability state declaration: expected 1 match, found {view_np.count(old_state)}")
view_np = view_np.replace(old_state, new_state, 1)

# Ability geometry: always-visible side detail. A-E is one continuous title box
# stretching to the full height of the F-P Description + Tags stack.
css_start = view_np.find("/* V31.133 Unit Ability side-detail layout in unified New View. */")
css_end_marker = ".unit-ability-tags.ability-active .weapon-tag{opacity:1}"
css_end = view_np.find(css_end_marker, css_start)
if css_start < 0 or css_end < 0:
    raise SystemExit("V31.133 Ability CSS bounds missing")
css_end += len(css_end_marker)
new_css = r'''/* V31.135 always-open Unit Ability side-detail layout in unified New View. */
.unit-ability-block{grid-column:1/span 16;z-index:4;box-sizing:border-box;align-self:start;display:grid;grid-template-columns:repeat(16,var(--cell));align-items:stretch;min-width:0;min-height:calc(var(--cell)*2);background:transparent;overflow:visible}
.unit-ability-button{grid-column:1/span 5;grid-row:1;box-sizing:border-box;align-self:stretch;min-width:0;min-height:calc(var(--cell)*2);height:auto;display:flex;align-items:center;justify-content:center;text-align:center;padding:4px 8px;white-space:normal;overflow:hidden;overflow-wrap:anywhere;background:var(--card);border:1px solid var(--border);border-radius:4px;color:rgba(241,243,244,.5);font:900 var(--body)/1 Roboto,Arial,sans-serif;cursor:pointer}
.unit-ability-button.ability-active{color:#80d6a3!important}
.unit-ability-detail{grid-column:6/span 11;grid-row:1;box-sizing:border-box;align-self:start;min-width:0;display:flex;flex-direction:column;align-items:stretch;background:transparent;overflow:visible}
.unit-ability-description-row{box-sizing:border-box;width:100%;min-width:0;min-height:calc(var(--cell)*2);display:flex;align-items:center;padding:4px 8px;white-space:normal;overflow:visible;overflow-wrap:anywhere;background:var(--card);border:1px solid var(--border);border-radius:4px;color:var(--secondary);font:700 var(--meta)/1.25 Roboto,Arial,sans-serif;cursor:pointer}
.unit-ability-tags{box-sizing:border-box;width:100%;min-width:0;min-height:var(--cell);display:flex;flex-wrap:wrap;align-items:center;align-content:center;justify-content:flex-start;gap:var(--gap);padding:1px 0;overflow:visible;background:transparent}
.unit-ability-tags .weapon-tag{height:auto;min-height:var(--std);max-width:100%;white-space:normal;overflow:visible;text-align:center;line-height:1.1;padding-top:4px;padding-bottom:4px}'''
view_np = view_np[:css_start] + new_css + view_np[css_end:]

# Replace only the Ability helper block. V31.131 Weapon Tag focus helpers begin
# at viewWeaponLayoutSyncDepth and remain untouched.
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
function newViewAbilityStateToken(key){
  return String(activeUnitIndex)+'::'+String(key||'');
}
function newViewAbilityIsActive(key){
  return activeAbilityKeys.has(newViewAbilityStateToken(key));
}
function newViewAbilityUsesLongDescription(key){
  return longAbilityDescriptionKeys.has(newViewAbilityStateToken(key));
}
function toggleNewViewAbilityActive(key){
  const clean=String(key||'');
  const token=newViewAbilityStateToken(clean);
  if(activeAbilityKeys.has(token)){
    activeAbilityKeys.delete(token);
    if(String(selectedAbilityKey)===clean)selectedAbilityKey=null;
  }else{
    activeAbilityKeys.add(token);
    selectedAbilityKey=clean;
  }
  syncWeaponLayout();
}
function toggleNewViewAbilityDescription(key){
  const token=newViewAbilityStateToken(key);
  if(longAbilityDescriptionKeys.has(token))longAbilityDescriptionKeys.delete(token);
  else longAbilityDescriptionKeys.add(token);
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
function makeNewViewAbilityBlock(startRow,key,ability,visibleTags,active,useLong){
  const block=document.createElement('div');
  block.className='unit-ability-block'+(active?' ability-active':'');
  block.dataset.abilityKey=String(key||'');
  block.style.gridColumn='1 / span 16';
  block.style.gridRow=String(startRow)+' / span 2';

  const button=document.createElement('div');
  button.className='unit-ability-button'+(active?' ability-active':'');
  button.textContent=String(ability&&ability.name||'');
  button.onclick=event=>{event.stopPropagation();toggleNewViewAbilityActive(key)};
  block.appendChild(button);

  const detail=document.createElement('div');
  detail.className='unit-ability-detail';

  const description=document.createElement('div');
  description.className='unit-ability-description-row';
  const descriptionText=useLong
    ? String(ability&&ability.longDescription||ability&&ability.description||'')
    : String(ability&&ability.shortDescription||ability&&ability.description||'');
  description.textContent=descriptionText;
  description.onclick=event=>{event.stopPropagation();toggleNewViewAbilityDescription(key)};
  detail.appendChild(description);

  if(visibleTags.length){
    const tags=document.createElement('div');
    tags.className='unit-ability-tags';
    visibleTags.forEach(tag=>{
      const badge=document.createElement('span');
      badge.className='weapon-tag';
      badge.textContent=String(tag&&tag.label||'');
      tags.appendChild(badge);
    });
    tags.onclick=event=>{event.stopPropagation()};
    detail.appendChild(tags);
  }
  block.appendChild(detail);

  grid.appendChild(block);
  const cellPx=parseFloat(getComputedStyle(grid).getPropertyValue('--cell'))||26;
  const naturalHeight=Math.max(cellPx*2,block.scrollHeight||0,detail.scrollHeight||0);
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
    const active=Boolean(key&&newViewAbilityIsActive(key));
    const useLong=Boolean(key&&newViewAbilityUsesLongDescription(key));
    const visibleTags=newViewAbilityVisibleTags(ability).filter(tag=>String(tag&&tag.label||'').trim());
    const rowSpan=makeNewViewAbilityBlock(cursor,key,ability,visibleTags,active,useLong);
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
    CHANGE NOTE - WH40k_11th_V31.135
    Scope: Unified New View Ability interaction/presentation only. Abilities are now always shown as side-detail blocks: title in A-E and Short Description/structured Tags in F-P. The A-E title box stretches continuously to the full height of the F-P Description + Tags stack. Tapping an Ability title independently toggles its muted/green Active state. Tapping its Description independently toggles between the Old Edit-authoritative Short and Long description text. Ability interactions no longer clear or otherwise touch Weapon selection. Tags, Ability filtering/order/data authority, the one-row gap after Weapons, V31.131 Weapon Tag focus, V31.134 muted-gray presentation, open-Unit focus/wrap behavior, and all other New View behavior remain unchanged.
    Risk areas: Unified New View Ability presentation/transient title and description state only. No Ability data editing, Weapon data/state behavior, Boyz data, Unit stats, Probable, lock/FIX, Cards, Waha, CSV data, persistence, or Version controls changed.
  -->

'''
marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.134\n"
if text.count(marker) != 1:
    raise SystemExit("V31.134 change-note insertion marker missing")
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
    "/* V31.135 always-open Unit Ability side-detail layout in unified New View. */",
    "/* V31.134 New View muted-gray presentation */",
    ".unit-ability-block{grid-column:1/span 16;",
    "grid-template-columns:repeat(16,var(--cell));align-items:stretch;",
    ".unit-ability-button{grid-column:1/span 5;grid-row:1;",
    "align-self:stretch;min-width:0;min-height:calc(var(--cell)*2);height:auto;",
    ".unit-ability-detail{grid-column:6/span 11;grid-row:1;",
    "const activeAbilityKeys=new Set();",
    "const longAbilityDescriptionKeys=new Set();",
    "function newViewAbilityIsActive(key){",
    "function newViewAbilityUsesLongDescription(key){",
    "function toggleNewViewAbilityActive(key){",
    "function toggleNewViewAbilityDescription(key){",
    "button.onclick=event=>{event.stopPropagation();toggleNewViewAbilityActive(key)};",
    "description.onclick=event=>{event.stopPropagation();toggleNewViewAbilityDescription(key)};",
    "const descriptionText=useLong",
    "ability&&ability.longDescription||ability&&ability.description",
    "ability&&ability.shortDescription||ability&&ability.description",
    "const abilityStartRow=weaponBottomRow+2;",
    "const active=Boolean(key&&newViewAbilityIsActive(key));",
    "const useLong=Boolean(key&&newViewAbilityUsesLongDescription(key));",
    "let viewWeaponLayoutSyncDepth=0;",
    "function applyViewWeaponTagFocus(){",
]:
    if expected not in final_view:
        raise SystemExit("V31.135 View acceptance failed: " + expected)

for forbidden in [
    "const openAbilityKeys=new Set();",
    "function newViewAbilityIsOpen(key){",
    "block.className='unit-ability-block'+(active?' ability-expanded ability-active':'');",
    "description.className='unit-ability-description-row ability-active';",
    ".unit-ability-description-row.ability-active{color:#80d6a3!important}",
]:
    if forbidden in final_view:
        raise SystemExit("V31.135 acceptance failed: old Ability open/active coupling remains: " + forbidden)

# Ability toggle helpers must not clear Weapon selection.
active_toggle = final_view[final_view.find("function toggleNewViewAbilityActive(key){"):final_view.find("function toggleNewViewAbilityDescription(key){")]
long_toggle = final_view[final_view.find("function toggleNewViewAbilityDescription(key){"):final_view.find("function newViewLastVisibleWeaponRow", final_view.find("function toggleNewViewAbilityDescription(key){"))]
if "selectedWeaponIndex=null" in active_toggle or "selectedWeaponIndex=null" in long_toggle:
    raise SystemExit("V31.135 acceptance failed: Ability interaction still clears Weapon selection")

for expected in [
    "shortDescription: String(effectiveItem.shortText || sourceItem.shortText || effectiveItem.text || sourceItem.text || effectiveItem.longText || sourceItem.longText || \"\"),",
    "longDescription: String(effectiveItem.longText || sourceItem.longText || effectiveItem.text || sourceItem.text || effectiveItem.shortText || sourceItem.shortText || \"\"),",
    "<title>WH40k 11th V31.135</title>",
    "The current baseline is WH40k_11th_V31.135;",
    'const APP_VERSION = "31.135";',
    "version: 'V31.135',",
    "CHANGE NOTE - WH40k_11th_V31.135",
]:
    if expected not in text:
        raise SystemExit("V31.135 release acceptance failed: " + expected)

path.write_text(text, encoding="utf-8")
print("Built V31.135: always-open side-detail Abilities with independent Active and Short/Long states")
