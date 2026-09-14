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
once("<title>WH40k 11th V31.123</title>", "<title>WH40k 11th V31.124</title>", "title")
once(
    "The current baseline is WH40k_11th_V31.123;",
    "The current baseline is WH40k_11th_V31.124;",
    "baseline",
)
once('const APP_VERSION = "31.123";', 'const APP_VERSION = "31.124";', "APP_VERSION")
once("version: 'V31.123',", "version: 'V31.124',", "quality version")

# ---------------------------------------------------------------------------
# Parent/model bridge: Old Edit remains authoritative for Unit Abilities.
# Resolve the same roster-aware Ability collection, effective overrides, order,
# hidden state, and structured Tags that Old Edit uses. New View receives only a
# display projection of that resolved state.
# ---------------------------------------------------------------------------
weapons_anchor = '''      const weapons = entry && unit ? getWeaponsForRosterEntry(entry, unit).filter(item => item && !item.isMissingLink) : [];
      return {'''
abilities_bridge = '''      const weapons = entry && unit ? getWeaponsForRosterEntry(entry, unit).filter(item => item && !item.isMissingLink) : [];
      const unitAbilities = entry && unit
        ? getAbilitiesForRosterEntry(entry, unit)
            .filter(ability => ability && !ability.isMissingLink)
            .map((ability, sequence) => {
              const sourceItem = getAbilitySourceItem(ability) || ability;
              const effectiveItem = getRosterEntryEffectiveAbility(entry, sourceItem) || sourceItem;
              const itemKey = getAbilityItemEditKey(sourceItem);
              const orderKey = getInnateAbilityOrderKey(sourceItem);
              let defaultOrder = getInnateAbilityDefaultSortOrder(sourceItem);
              if (abilityHasPromotedUnitLevelRule(effectiveItem)) defaultOrder = 8;
              const sourceRef = normalizeRosterSentItemRef({ kind: "ability", key: itemKey });
              if (sourceRef && rosterEntryHasHiddenSource(entry, sourceRef)) return null;
              const order = getRosterEntryAbilitySortOrder(entry, orderKey, defaultOrder);
              if (order === 8 || order === 9) return null;
              const tags = getAbilityProtectedModifierTagAssignments(effectiveItem).map(assignment => {
                const definition = getTagDefinitionByTagAndCategory(assignment.tag, assignment.category);
                if (isPromotedUnitLevelTag(assignment.tag, definition)) return null;
                return {
                  label: getAbilityTagDisplayLabel(assignment.tag),
                  category: String(assignment.category || ""),
                  scope: getTagDefinitionWeaponScope(definition, assignment.category).kind
                };
              }).filter(Boolean);
              return {
                abilityId: String(sourceItem.abilityId || itemKey || ""),
                key: String(itemKey || sourceItem.abilityId || sourceItem.name || sequence),
                name: String(effectiveItem.name || sourceItem.name || sourceItem.abilityId || ""),
                description: String(effectiveItem.shortText || effectiveItem.text || effectiveItem.longText || sourceItem.shortText || sourceItem.text || sourceItem.longText || ""),
                order,
                sequence,
                tags
              };
            })
            .filter(Boolean)
            .sort((a, b) => (a.order - b.order) || (a.sequence - b.sequence))
        : [];
      return {'''
once(weapons_anchor, abilities_bridge, "Old Edit Ability bridge insertion")

core_anchor = '''        coreAbilities: unit ? getCoreAbilitiesForUnit(unit)
          .filter(ability => ability && !ability.isMissingLink)
          .map(ability => ({ name: String(ability.name || ability.abilityId || "") })) : [],
        weapons: weapons.map(weapon => {'''
core_with_abilities = '''        coreAbilities: unit ? getCoreAbilitiesForUnit(unit)
          .filter(ability => ability && !ability.isMissingLink)
          .map(ability => ({ name: String(ability.name || ability.abilityId || "") })) : [],
        abilities: unitAbilities,
        weapons: weapons.map(weapon => {'''
once(core_anchor, core_with_abilities, "Ability bridge return field")

# ---------------------------------------------------------------------------
# Unified New View iframe presentation.
# ---------------------------------------------------------------------------
view_pat = re.compile(
    r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)',
    re.S,
)
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing")
view_np = html.unescape(vm.group(2))

for required in [
    "let selectedWeaponIndex=null;",
    "function syncWeaponLayout(){",
    "function syncViewSelectionPresentation(){",
    "function applyViewFocusSpacing(){",
    ".weapon-tags{min-height:var(--cell);",
    ".weapon-tag{",
    "const syncWeaponLayoutV31119=syncWeaponLayout;",
]:
    if required not in view_np:
        raise SystemExit("V31.124 baseline contract missing: " + required)

# Existing design system only: full-width rows, existing typography variables,
# existing muted/green colors, and the exact Weapon Tag box class for Tags.
ability_css = r'''
/* V31.124 Unit Abilities in unified New View. */
.unit-ability-name-row,.unit-ability-description-row{grid-column:1/span 16;z-index:4;box-sizing:border-box;min-height:var(--cell);display:flex;align-items:center;padding:0 8px;overflow:hidden;font-family:Roboto,Arial,sans-serif}
.unit-ability-name-row{font-size:var(--body);font-weight:900;line-height:1.1;color:var(--text);cursor:pointer}
.unit-ability-description-row{font-size:var(--meta);font-weight:700;line-height:1.25;color:var(--secondary);white-space:normal;overflow-wrap:anywhere;align-items:flex-start;padding-top:5px;padding-bottom:5px;cursor:pointer}
.unit-ability-tags{grid-column:1/span 16;z-index:4;cursor:pointer}
.unit-ability-name-row.ability-muted,.unit-ability-description-row.ability-muted{opacity:.5}
.unit-ability-tags.ability-muted .weapon-tag{color:var(--muted)}
.unit-ability-name-row.ability-active,.unit-ability-description-row.ability-active{color:#80d6a3;opacity:1}
.unit-ability-tags.ability-active .weapon-tag{opacity:1}
'''
if ".unit-ability-name-row" in view_np:
    raise SystemExit("V31.124 Ability CSS already present")
if view_np.count("</style>") < 1:
    raise SystemExit("Unified View style close marker missing")
view_np = view_np.replace("</style>", ability_css + "</style>", 1)

# Ability selection is presentation-only and shares one active selection with
# Weapons. The source data/state remains owned by Old Edit.
once_js = "let selectedWeaponIndex=null;"
view_np = view_np.replace(once_js, once_js + "\nlet selectedAbilityKey=null;", 1)

# Clear Ability selection anywhere the established code clears Weapon selection
# (filter changes, Unit changes, roster refreshes, lock snapshot generation).
view_np = view_np.replace("selectedWeaponIndex=null;", "selectedWeaponIndex=null;selectedAbilityKey=null;")
# The declaration replacement above is intentionally restored to valid separate
# declarations after the broad assignment replacement.
view_np = view_np.replace(
    "let selectedWeaponIndex=null;selectedAbilityKey=null;\nlet selectedAbilityKey=null;",
    "let selectedWeaponIndex=null;\nlet selectedAbilityKey=null;",
    1,
)

old_select_weapon = '''function selectWeapon(index){
  selectedWeaponIndex=selectedWeaponIndex===index?null:index;
  syncWeaponLayout();
}'''
new_select_weapon = '''function selectWeapon(index){
  selectedAbilityKey=null;
  selectedWeaponIndex=selectedWeaponIndex===index?null:index;
  syncWeaponLayout();
}'''
once_count = view_np.count(old_select_weapon)
if once_count != 1:
    raise SystemExit(f"Weapon selection function: expected 1 match, found {once_count}")
view_np = view_np.replace(old_select_weapon, new_select_weapon, 1)

helper_anchor = "function syncViewSelectionPresentation(){"
if view_np.count(helper_anchor) != 1:
    raise SystemExit("Ability helper insertion marker missing")

ability_helpers = r'''function clearNewViewAbilityRows(){
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
function newViewAbilityDescriptionSpan(value){
  const text=String(value||'').trim();
  if(!text)return 0;
  const lines=text.split(/\n/).reduce((total,line)=>total+Math.max(1,Math.ceil(String(line).length/56)),0);
  return Math.max(1,Math.min(6,lines));
}
function selectNewViewAbility(key){
  const clean=String(key||'');
  selectedWeaponIndex=null;
  selectedAbilityKey=selectedAbilityKey===clean?null:clean;
  syncWeaponLayout();
}
function makeNewViewAbilityRow(className,row,key,text,active){
  const el=document.createElement('div');
  el.className=className+' '+(active?'ability-active':'ability-muted');
  el.dataset.abilityKey=String(key||'');
  el.style.gridRow=String(row);
  el.textContent=String(text||'');
  el.onclick=event=>{event.stopPropagation();selectNewViewAbility(key)};
  grid.appendChild(el);
  return el;
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
  const abilities=(Array.isArray(data.abilities)?data.abilities:[]).filter(newViewAbilityMatchesFilter);
  if(selectedAbilityKey&&!abilities.some(ability=>String(ability&&ability.key||'')===String(selectedAbilityKey)))selectedAbilityKey=null;

  let cursor=detailStartRow+1;
  abilities.forEach(ability=>{
    const key=String(ability&&ability.key||ability&&ability.abilityId||'');
    const active=Boolean(key&&String(selectedAbilityKey)===key);
    makeNewViewAbilityRow('unit-ability-name-row',cursor++,key,ability&&ability.name,active);

    const description=String(ability&&ability.description||'').trim();
    const descriptionSpan=newViewAbilityDescriptionSpan(description);
    if(descriptionSpan){
      const descriptionRow=makeNewViewAbilityRow('unit-ability-description-row',cursor,key,description,active);
      descriptionRow.style.gridRow=String(cursor)+' / span '+String(descriptionSpan);
      cursor+=descriptionSpan;
    }

    const visibleTags=newViewAbilityVisibleTags(ability).filter(tag=>String(tag&&tag.label||'').trim());
    if(visibleTags.length){
      const tagRow=document.createElement('div');
      tagRow.className='weapon-tags unit-ability-tags '+(active?'ability-active':'ability-muted');
      tagRow.dataset.abilityKey=key;
      tagRow.style.display='flex';
      tagRow.style.gridRow=String(cursor++);
      visibleTags.forEach(tag=>{
        const badge=document.createElement('span');
        badge.className='weapon-tag';
        badge.textContent=String(tag.label||'');
        tagRow.appendChild(badge);
      });
      tagRow.onclick=event=>{event.stopPropagation();selectNewViewAbility(key)};
      grid.appendChild(tagRow);
    }
  });

  const abilityRows=cursor-(detailStartRow+1);
  if(abilityRows>0){
    const shifted=new Set();
    const shift=el=>{
      if(!el||shifted.has(el)||!viewPresentationVisible(el))return;
      shifted.add(el);
      const row=parseInt(el.style.gridRow||getComputedStyle(el).gridRowStart,10);
      if(Number.isFinite(row))el.style.gridRow=String(row+abilityRows);
    };
    shift(grid.querySelector('.weapon-header:not(.boyz-subunit-node)'));
    grid.querySelectorAll('.weapon-row,.weapon-tags:not(.unit-ability-tags),.boyz-subunit-node').forEach(shift);
  }

  let bottomRow=detailStartRow;
  grid.querySelectorAll('.unit-ability-name-row,.unit-ability-description-row,.unit-ability-tags,.weapon-header,.weapon-row,.weapon-tags,.boyz-subunit-node').forEach(el=>{
    if(!viewPresentationVisible(el))return;
    const row=parseInt(el.style.gridRow||getComputedStyle(el).gridRowStart,10);
    if(!Number.isFinite(row))return;
    const spanMatch=String(el.style.gridRow||'').match(/span\s+(\d+)/i);
    const span=spanMatch?Math.max(1,Number(spanMatch[1])||1):1;
    bottomRow=Math.max(bottomRow,row+span-1);
  });
  syncExpandedLayout(Math.max(1,bottomRow-detailStartRow+1));
  return abilityRows;
}
'''
view_np = view_np.replace(helper_anchor, ability_helpers + "\n" + helper_anchor, 1)

# New Ability rows belong inside both the open-Unit focus spacing and the open
# Unit overlay border.
old_focus_nodes = "grid.querySelectorAll('.weapon-row,.weapon-tags,.boyz-subunit-node').forEach(addContentNode);"
new_focus_nodes = "grid.querySelectorAll('.unit-ability-name-row,.unit-ability-description-row,.unit-ability-tags,.weapon-row,.weapon-tags,.boyz-subunit-node').forEach(addContentNode);"
once_count = view_np.count(old_focus_nodes)
if once_count != 1:
    raise SystemExit(f"focus content selector: expected 1 match, found {once_count}")
view_np = view_np.replace(old_focus_nodes, new_focus_nodes, 1)

old_wrap_nodes = "grid.querySelectorAll('.weapon-row,.weapon-tags,.boyz-subunit-node').forEach(el=>{"
new_wrap_nodes = "grid.querySelectorAll('.unit-ability-name-row,.unit-ability-description-row,.unit-ability-tags,.weapon-row,.weapon-tags,.boyz-subunit-node').forEach(el=>{"
once_count = view_np.count(old_wrap_nodes)
if once_count != 1:
    raise SystemExit(f"open Unit wrap selector: expected 1 match, found {once_count}")
view_np = view_np.replace(old_wrap_nodes, new_wrap_nodes, 1)

# Render/reflow Abilities after the established Weapon/Boyz layout is built and
# before V31.123 focus spacing is applied.
old_sync_wrapper = r'''syncWeaponLayout=function(){
  const focusLocked=typeof newViewHeaderLocked!=='undefined'&&newViewHeaderLocked;
  if(!focusLocked)clearViewFocusSpacing();
  const result=syncWeaponLayoutV31119.apply(this,arguments);
  if(!focusLocked)applyViewFocusSpacing();
  syncViewSelectionPresentation();
  return result;
};'''
new_sync_wrapper = r'''syncWeaponLayout=function(){
  const focusLocked=typeof newViewHeaderLocked!=='undefined'&&newViewHeaderLocked;
  if(!focusLocked)clearViewFocusSpacing();
  const result=syncWeaponLayoutV31119.apply(this,arguments);
  renderNewViewAbilitiesAndReflow();
  if(!focusLocked)applyViewFocusSpacing();
  syncViewSelectionPresentation();
  return result;
};'''
once_count = view_np.count(old_sync_wrapper)
if once_count != 1:
    raise SystemExit(f"Ability sync wrapper: expected 1 match, found {once_count}")
view_np = view_np.replace(old_sync_wrapper, new_sync_wrapper, 1)

text = text[: vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2) :]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.124
    Scope: Display normal Unit Abilities in unified New View using Old Edit as the authoritative resolved source. Visible Abilities follow the same roster-aware effective values, hidden state, and order used by Old Edit; effective orders 8 and 9 remain hidden. Each Ability renders between the Unit detail row and Weapons as Ability name, Short Description, then a dedicated structured-Tag row reusing the existing Weapon Tag boxes. Ability rows start muted and share one transient active selection with Weapons. Range/Melee/Other/All filtering applies to Abilities from structured Tag scope; mixed scoped Abilities show only the selected scope's Tags. Ability rows are included inside the existing open-Unit wrap and V31.123 focus separators.
    Risk areas: Unified New View Unit Ability display, filtering, transient Ability/Weapon selection presentation, expanded-Unit row sizing, and focus-wrap inclusion. Old Edit remains authoritative; no CSV schema, Ability editing, saved roster data, Probable mechanics, Cards, Waha, Version controls, or Unit/Weapon source data changes.
  -->

'''
marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.123\n"
if text.count(marker) != 1:
    raise SystemExit("V31.123 change-note insertion marker missing")
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

# Acceptance checks.
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing after writeback")
final_view = html.unescape(vm.group(2))
for expected in [
    "let selectedAbilityKey=null;",
    ".unit-ability-name-row,.unit-ability-description-row{grid-column:1/span 16;",
    "function renderNewViewAbilitiesAndReflow(){",
    "function selectNewViewAbility(key){",
    "weapon-tags unit-ability-tags",
    "renderNewViewAbilitiesAndReflow();",
    "'.unit-ability-name-row,.unit-ability-description-row,.unit-ability-tags,.weapon-row,.weapon-tags,.boyz-subunit-node'",
    "if(!focusLocked)applyViewFocusSpacing();",
    "syncViewSelectionPresentation();",
]:
    if expected not in final_view:
        raise SystemExit("V31.124 View acceptance failed: " + expected)

for expected in [
    "const unitAbilities = entry && unit",
    "getAbilitiesForRosterEntry(entry, unit)",
    "getRosterEntryEffectiveAbility(entry, sourceItem)",
    "getRosterEntryAbilitySortOrder(entry, orderKey, defaultOrder)",
    "if (order === 8 || order === 9) return null;",
    "abilities: unitAbilities,",
    "<title>WH40k 11th V31.124</title>",
    "The current baseline is WH40k_11th_V31.124;",
    'const APP_VERSION = "31.124";',
    "version: 'V31.124',",
    "CHANGE NOTE - WH40k_11th_V31.124",
]:
    if expected not in text:
        raise SystemExit("V31.124 release acceptance failed: " + expected)

path.write_text(text, encoding="utf-8")
print("Built V31.124: Old Edit-derived Unit Abilities now render in unified New View")
