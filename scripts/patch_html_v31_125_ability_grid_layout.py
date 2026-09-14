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
replace_once("<title>WH40k 11th V31.124</title>", "<title>WH40k 11th V31.125</title>", "title")
replace_once("The current baseline is WH40k_11th_V31.124;", "The current baseline is WH40k_11th_V31.125;", "baseline")
replace_once('const APP_VERSION = "31.124";', 'const APP_VERSION = "31.125";', "APP_VERSION")
replace_once("version: 'V31.124',", "version: 'V31.125',", "quality version")

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing")
view_np = html.unescape(vm.group(2))

# Replace the complete V31.124 Ability-only CSS block by marker rather than by
# an exact whitespace match. All values below come from the existing New View
# design system and existing Weapon/Tag treatments.
css_start = view_np.find("/* V31.124 Unit Abilities in unified New View. */")
css_end_marker = ".unit-ability-tags.ability-active .weapon-tag{opacity:1}"
css_end = view_np.find(css_end_marker, css_start)
if css_start < 0 or css_end < 0:
    raise SystemExit("V31.124 Ability CSS bounds missing")
css_end += len(css_end_marker)
new_css = r'''/* V31.125 Unit Ability grid layout in unified New View. */
.unit-ability-name-row{grid-column:1/span 6;z-index:4;box-sizing:border-box;align-self:stretch;display:flex;align-items:center;justify-content:center;text-align:center;padding:0 8px;overflow:hidden;background:var(--card);border-right:1px solid var(--border);border-bottom:1px solid var(--border);color:var(--text);font:900 var(--body)/1 Roboto,Arial,sans-serif;cursor:pointer}
.unit-ability-description-row{grid-column:7/span 10;z-index:4;box-sizing:border-box;align-self:stretch;display:flex;align-items:center;padding:0 8px;overflow:hidden;white-space:normal;overflow-wrap:anywhere;background:var(--card);border-bottom:1px solid var(--border);color:var(--secondary);font:700 var(--meta)/1.25 Roboto,Arial,sans-serif;cursor:pointer}
.unit-ability-tags{grid-column:7/span 10;z-index:4;box-sizing:border-box;align-self:stretch;background:var(--card);border-top:1px solid var(--border);border-bottom:1px solid var(--border);cursor:pointer}
.unit-ability-name-row.ability-muted,.unit-ability-description-row.ability-muted{color:rgba(241,243,244,.5)!important}
.unit-ability-tags.ability-muted .weapon-tag{color:rgba(154,160,166,.5)!important}
.unit-ability-name-row.ability-active,.unit-ability-description-row.ability-active{color:#80d6a3!important}
.unit-ability-tags.ability-active .weapon-tag{opacity:1}'''
view_np = view_np[:css_start] + new_css + view_np[css_end:]

# Replace only the V31.124 Ability helper block. Existing Weapon rendering is
# left untouched; this renderer simply appends Ability blocks below its final
# visible row and extends the same grid expansion calculation.
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

    makeNewViewAbilityCell('unit-ability-name-row',cursor,blockRows,key,ability&&ability.name,active);
    makeNewViewAbilityCell('unit-ability-description-row',cursor,2,key,ability&&ability.description,active);

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
text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.125
    Scope: Redesign unified New View Unit Ability layout using the existing New View grid/design system. Abilities now render after all visible Weapons and Weapon Tags. Every Ability occupies exactly two grid rows, or three when it has visible structured Tags. The Ability name is one centered A-F cell spanning the full two/three-row Ability block. The Short Description occupies G-P across the first two rows. When Tags exist, G-P row three uses the existing Weapon Tag boxes. Existing New View fonts, card background, borders, muted/active colors, grid dimensions, Tag boxes, Old Edit authoritative Ability data/order, filtering, and transient Ability/Weapon selection are retained.
    Risk areas: Unified New View Ability geometry/order and expanded-Unit height only. No Old Edit, CSV schema/data, Weapon layout/data, Unit stats, Probable mechanics, Cards, Waha, Version controls, persistence, lock behavior, or report storage changes.
  -->

'''
marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.124\n"
if marker not in text:
    raise SystemExit("V31.124 change-note insertion marker missing")
text = text.replace(marker, note + marker, 1)

notes = list(re.finditer(r"\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n", text, re.S))
for match in reversed(notes[5:]):
    text = text[:match.start()] + text[match.end():]

# Focused acceptance checks for the requested geometry and placement.
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified View missing after writeback")
final_view = html.unescape(vm.group(2))
checks = [
    ".unit-ability-name-row{grid-column:1/span 6;",
    "justify-content:center;text-align:center;",
    ".unit-ability-description-row{grid-column:7/span 10;",
    ".unit-ability-tags{grid-column:7/span 10;",
    "const blockRows=visibleTags.length?3:2;",
    "makeNewViewAbilityCell('unit-ability-name-row',cursor,blockRows",
    "makeNewViewAbilityCell('unit-ability-description-row',cursor,2",
    "tagRow.className='weapon-tags unit-ability-tags '",
    "tagRow.style.gridRow=String(cursor+2);",
    "const weaponBottomRow=newViewLastVisibleWeaponRow(detailStartRow);",
    "let cursor=weaponBottomRow+1;",
]
for expected in checks:
    if expected not in final_view:
        raise SystemExit("V31.125 acceptance failed: " + expected)

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
print("Built V31.125: A-F centered Ability name, G-P two-row description, optional third-row Tags, all after Weapons")
