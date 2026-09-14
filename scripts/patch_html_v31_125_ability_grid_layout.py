from pathlib import Path
import html
import re

path = Path("WH40k_11th.html")
text = path.read_text(encoding="utf-8")


def once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    text = text.replace(old, new, 1)


# Sequential release metadata.
once("<title>WH40k 11th V31.124</title>", "<title>WH40k 11th V31.125</title>", "title")
once(
    "The current baseline is WH40k_11th_V31.124;",
    "The current baseline is WH40k_11th_V31.125;",
    "baseline",
)
once('const APP_VERSION = "31.124";', 'const APP_VERSION = "31.125";', "APP_VERSION")
once("version: 'V31.124',", "version: 'V31.125',", "quality version")

view_pat = re.compile(
    r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)',
    re.S,
)
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing")
view_np = html.unescape(vm.group(2))

# Replace only the V31.124 Ability presentation CSS. Use the same New View
# design tokens, typography, borders, card background, active green, muted text,
# and existing Weapon Tag boxes already used elsewhere in the page.
old_css = r'''/* V31.124 Unit Abilities in unified New View. */
.unit-ability-name-row,.unit-ability-description-row{grid-column:1/span 16;z-index:4;box-sizing:border-box;min-height:var(--cell);display:flex;align-items:center;padding:0 8px;overflow:hidden;font-family:Roboto,Arial,sans-serif}
.unit-ability-name-row{font-size:var(--body);font-weight:900;line-height:1.1;color:var(--text);cursor:pointer}
.unit-ability-description-row{font-size:var(--meta);font-weight:700;line-height:1.25;color:var(--secondary);white-space:normal;overflow-wrap:anywhere;align-items:flex-start;padding-top:5px;padding-bottom:5px;cursor:pointer}
.unit-ability-tags{grid-column:1/span 16;z-index:4;cursor:pointer}
.unit-ability-name-row.ability-muted,.unit-ability-description-row.ability-muted{opacity:.5}
.unit-ability-tags.ability-muted .weapon-tag{color:var(--muted)}
.unit-ability-name-row.ability-active,.unit-ability-description-row.ability-active{color:#80d6a3;opacity:1}
.unit-ability-tags.ability-active .weapon-tag{opacity:1}
'''
new_css = r'''/* V31.125 Unit Ability grid layout in unified New View. */
.unit-ability-name-row{grid-column:1/span 6;z-index:4;box-sizing:border-box;align-self:stretch;display:flex;align-items:center;justify-content:center;text-align:center;padding:0 8px;overflow:hidden;background:var(--card);border-right:1px solid var(--border);border-bottom:1px solid var(--border);color:var(--text);font:900 var(--body)/1 Roboto,Arial,sans-serif;cursor:pointer}
.unit-ability-description-row{grid-column:7/span 10;z-index:4;box-sizing:border-box;align-self:stretch;display:flex;align-items:center;padding:0 8px;overflow:hidden;white-space:normal;overflow-wrap:anywhere;background:var(--card);border-bottom:1px solid var(--border);color:var(--secondary);font:700 var(--meta)/1.25 Roboto,Arial,sans-serif;cursor:pointer}
.unit-ability-tags{grid-column:7/span 10;z-index:4;box-sizing:border-box;align-self:stretch;background:var(--card);border-top:1px solid var(--border);border-bottom:1px solid var(--border);cursor:pointer}
.unit-ability-name-row.ability-muted,.unit-ability-description-row.ability-muted{color:rgba(241,243,244,.5)!important}
.unit-ability-tags.ability-muted .weapon-tag{color:rgba(154,160,166,.5)!important}
.unit-ability-name-row.ability-active,.unit-ability-description-row.ability-active{color:#80d6a3!important}
.unit-ability-tags.ability-active .weapon-tag{opacity:1}
'''
once(old_css, new_css, "Ability layout CSS")

# Replace the V31.124 Ability renderer as one bounded helper block. Weapons remain
# authoritative for their own rows. Abilities are appended after the final
# visible Weapon/Weapon Tag row, never inserted before or between Weapons.
helper_start = view_np.find("function clearNewViewAbilityRows(){")
helper_end = view_np.find("function syncViewSelectionPresentation(){", helper_start)
if helper_start < 0 or helper_end < 0:
    raise SystemExit("V31.124 Ability helper bounds missing")

new_helpers = r'''function clearNewViewAbilityRows(){
  grid.querySelectorAll('.unit-ability-name-row,.unit-ability-description-row,.unit-ability-tags').forEach(el=>el.remove());
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
function makeNewViewAbilityCell(className,startRow,rowSpan,key,text,active){
  const el=document.createElement('div');
  el.className=className+' '+(active?'ability-active':'ability-muted');
  el.dataset.abilityKey=String(key||'');
  el.style.gridRow=String(startRow)+(rowSpan>1?' / span '+String(rowSpan):'');
  el.textContent=String(text||'');
  el.onclick=event=>{event.stopPropagation();selectNewViewAbility(key)};
  grid.appendChild(el);
  return el;
}
function newViewLastVisibleWeaponRow(detailStartRow){
  let bottom=detailStartRow;
  grid.querySelectorAll('.weapon-header,.weapon-row,.weapon-tags:not(.unit-ability-tags),.boyz-subunit-node').forEach(el=>{
    if(!viewPresentationVisible(el))return;
    const row=parseInt(el.style.gridRow||getComputedStyle(el).gridRowStart,10);
    if(!Number.isFinite(row))return;
    const spanMatch=String(el.style.gridRow||'').match(/span\s+(\d+)/i);
    const span=spanMatch?Math.max(1,Number(spanMatch[1])||1):1;
    bottom=Math.max(bottom,row+span-1);
  });
  return bottom;
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
    const blockRows=visibleTags.length?3:2;

    // A-F: one centered Ability-name cell spanning the full 2/3-row block.
    makeNewViewAbilityCell('unit-ability-name-row',cursor,blockRows,key,ability&&ability.name,active);

    // G-P: Short Description always occupies exactly the first two rows.
    makeNewViewAbilityCell('unit-ability-description-row',cursor,2,key,ability&&ability.description,active);

    // G-P row 3 exists only when structured Tags are visible. Reuse the exact
    // existing Weapon Tag element class/box treatment.
    if(visibleTags.length){
      const tagRow=document.createElement('div');
      tagRow.className='weapon-tags unit-ability-tags '+(active?'ability-active':'ability-muted');
      tagRow.dataset.abilityKey=key;
      tagRow.style.display='flex';
      tagRow.style.gridRow=String(cursor+2);
      visibleTags.forEach(tag=>{
        const badge=document.createElement('span');
        badge.className='weapon-tag';
        badge.textContent=String(tag.label||'');
        tagRow.appendChild(badge);
      });
      tagRow.onclick=event=>{event.stopPropagation();selectNewViewAbility(key)};
      grid.appendChild(tagRow);
    }

    cursor+=blockRows;
  });

  const finalBottomRow=abilities.length?cursor-1:weaponBottomRow;
  syncExpandedLayout(Math.max(1,finalBottomRow-detailStartRow+1));
  if(typeof syncNewViewFrameHeight==='function')syncNewViewFrameHeight();
  return Math.max(0,cursor-firstAbilityRow);
}
'''
view_np = view_np[:helper_start] + new_helpers + "\n" + view_np[helper_end:]

# Write unified View back into the HTML.
text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.125
    Scope: Redesign unified New View Unit Ability layout using the existing New View grid/design system. Abilities now render after all visible Weapons and Weapon Tags. Every Ability occupies exactly two grid rows, or three when it has visible structured Tags. The Ability name is one centered A-F cell spanning the full two/three-row Ability block. The Short Description occupies G-P across the first two rows. When Tags exist, G-P row three uses the existing Weapon Tag boxes. Existing New View fonts, card background, borders, muted/active colors, grid dimensions, Tag boxes, Old Edit authoritative Ability data/order, filtering, and transient Ability/Weapon selection are retained.
    Risk areas: Unified New View Ability geometry/order and expanded-Unit height only. No Old Edit, CSV schema/data, Weapon layout/data, Unit stats, Probable mechanics, Cards, Waha, Version controls, persistence, lock behavior, or report storage changes.
  -->

'''
marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.124\n"
if text.count(marker) != 1:
    raise SystemExit("V31.124 change-note insertion marker missing")
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
    text = text[:match.start()] + text[match.end():]

# Acceptance checks.
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing after writeback")
final_view = html.unescape(vm.group(2))

for expected in [
    ".unit-ability-name-row{grid-column:1/span 6;",
    "justify-content:center;text-align:center;",
    "font:900 var(--body)/1 Roboto,Arial,sans-serif",
    ".unit-ability-description-row{grid-column:7/span 10;",
    "font:700 var(--meta)/1.25 Roboto,Arial,sans-serif",
    ".unit-ability-tags{grid-column:7/span 10;",
    "tagRow.className='weapon-tags unit-ability-tags '",
    "const blockRows=visibleTags.length?3:2;",
    "makeNewViewAbilityCell('unit-ability-name-row',cursor,blockRows",
    "makeNewViewAbilityCell('unit-ability-description-row',cursor,2",
    "tagRow.style.gridRow=String(cursor+2);",
    "const weaponBottomRow=newViewLastVisibleWeaponRow(detailStartRow);",
    "let cursor=weaponBottomRow+1;",
    "syncExpandedLayout(Math.max(1,finalBottomRow-detailStartRow+1));",
]:
    if expected not in final_view:
        raise SystemExit("V31.125 Ability layout acceptance failed: " + expected)

for forbidden in [
    "/* V31.124 Unit Abilities in unified New View. */",
    "grid-column:1/span 16;z-index:4;box-sizing:border-box;min-height:var(--cell);display:flex;align-items:center;padding:0 8px;overflow:hidden;font-family:Roboto,Arial,sans-serif",
    "const descriptionSpan=newViewAbilityDescriptionSpan(description);",
]:
    if forbidden in final_view:
        raise SystemExit("V31.125 retained old Ability layout: " + forbidden)

for expected in [
    "<title>WH40k 11th V31.125</title>",
    "The current baseline is WH40k_11th_V31.125;",
    'const APP_VERSION = "31.125";',
    "version: 'V31.125',",
    "CHANGE NOTE - WH40k_11th_V31.125",
]:
    if expected not in text:
        raise SystemExit("V31.125 release acceptance failed: " + expected)

path.write_text(text, encoding="utf-8")
print("Built V31.125: Unit Abilities use A-F / G-P fixed 2/3-row grid blocks after Weapons")
