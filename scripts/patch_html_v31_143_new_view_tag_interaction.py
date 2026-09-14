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
replace_once("<title>WH40k 11th V31.142</title>", "<title>WH40k 11th V31.143</title>", "title")
replace_once(
    "The current baseline is WH40k_11th_V31.142;",
    "The current baseline is WH40k_11th_V31.143;",
    "baseline",
)
replace_once('const APP_VERSION = "31.142";', 'const APP_VERSION = "31.143";', "APP_VERSION")
replace_once("version: 'V31.142',", "version: 'V31.143',", "quality version")

# Parent/runtime bridge: New View writes to the same roster Tag state that Old View uses.
bridge_marker = "    window.getNewViewFixReportItems = function() {"
if text.count(bridge_marker) != 1:
    raise SystemExit("New View bridge insertion marker missing")
bridge = r'''    window.toggleAlternateViewAbilityTag = function(payload = {}) {
      if (appEditMode) return { ok: false };
      const roster = getActiveRoster();
      const entryId = String(payload.entryId || "").trim();
      const sourceKind = String(payload.sourceKind || "ability").trim().toLowerCase() || "ability";
      const itemKey = String(payload.itemKey || "").trim();
      const tag = String(payload.tag || "").trim();
      const category = String(payload.category || "").trim();
      const defaultOn = payload.defaultOn !== false;
      const entry = getRosterEntryById(roster, entryId);
      const ability = resolveRosterTaggedSourceAbility(sourceKind, itemKey, roster, entry);
      if (!entry || !ability || !tag) return { ok: false };

      const current = getRosterEntryAbilityTagState(entry, ability, tag, defaultOn, category);
      const next = !current;
      if (!setRosterEntryAbilityTagState(entry, ability, tag, next, defaultOn, category)) return { ok: false };
      rosterWorkingStateDirty = true;
      invalidateRosterModeDomCache("view");
      invalidateRosterModeDomCache("edit");
      persistRosterLibrary({ reason: "new-view-ability-tag", skipNoteDeleteFinalize: true });
      return { ok: true, active: next };
    };

    window.toggleAlternateViewWeaponTag = function(payload = {}) {
      if (appEditMode) return { ok: false };
      const roster = getActiveRoster();
      const entryId = String(payload.entryId || "").trim();
      const weaponKey = String(payload.weaponKey || payload.weaponId || "").trim();
      const tag = String(payload.tag || "").trim();
      const entry = getRosterEntryById(roster, entryId);
      if (!entry || !weaponKey || !tag) return { ok: false };
      if (isInnateWeaponAbilityTag(weaponKey, tag)) return { ok: false, locked: true, active: true };

      const current = getRosterEntryWeaponTagState(entry, weaponKey, tag, true);
      const next = !current;
      if (!setRosterEntryWeaponTagState(entry, weaponKey, tag, next, true)) return { ok: false };
      rosterWorkingStateDirty = true;
      invalidateRosterModeDomCache("view");
      invalidateRosterModeDomCache("edit");
      persistRosterLibrary({ reason: "new-view-weapon-tag", skipNoteDeleteFinalize: true });
      return { ok: true, active: next };
    };

'''
text = text.replace(bridge_marker, bridge + bridge_marker, 1)

view_pat = re.compile(
    r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)',
    re.S,
)
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing")
view_np = html.unescape(vm.group(2))

# Baseline contracts from Phase 1/V31.142.
for required in [
    "function newViewProcessingLocked(){return Boolean(newViewHeaderLocked&&activePageMode==='view')}",
    "const displayActive=weaponSelected&&tagActive;",
    "badge.className='weapon-tag ability-tag-state '+(tagActive?'tag-state-on':'tag-state-off')",
    "tags.onclick=event=>{event.stopPropagation()};",
    "function makeBoyzWeaponTags(template,weapon){",
    "function refreshAlternateViewUnitsFromParent(){if(newViewProcessingLocked())return false;",
]:
    if required not in view_np:
        raise SystemExit("V31.143 baseline contract missing: " + required)

# Add state-preserving New View Tag interaction helpers immediately after the
# existing Ability description toggle. Lock is a hard gate before any parent write.
old_helpers = """function toggleNewViewAbilityDescription(key){
  const token=newViewAbilityStateToken(key);
  if(longAbilityDescriptionKeys.has(token))longAbilityDescriptionKeys.delete(token);
  else longAbilityDescriptionKeys.add(token);
  syncWeaponLayout();
}
"""
new_helpers = old_helpers + """function refreshNewViewAfterTagMutation(){
  if(newViewProcessingLocked())return false;
  const currentData=activeUnitIndex===null?null:unitDataByIndex[activeUnitIndex];
  const savedEntryId=String(currentData&&currentData.entryId||'');
  const savedWeapon=selectedWeaponIndex!==null&&currentData&&Array.isArray(currentData.weapons)?currentData.weapons[selectedWeaponIndex-1]:null;
  const savedWeaponId=String(savedWeapon&&savedWeapon.weaponId||'');
  const savedAbility=selectedAbilityKey;
  let rows=[];
  try{rows=parent&&typeof parent.getAlternateViewRosterRows==='function'?parent.getAlternateViewRosterRows():[]}catch(_){rows=[]}
  const ok=renderNewViewRosterRows(rows);
  if(savedEntryId){
    const restoredIndex=rows.findIndex(row=>row&&row.kind==='unit'&&String(row.entryId||'')===savedEntryId);
    if(restoredIndex>=0)activeUnitIndex=restoredIndex;
  }
  selectedWeaponIndex=null;
  const restoredData=activeUnitIndex===null?null:unitDataByIndex[activeUnitIndex];
  if(savedWeaponId&&restoredData&&Array.isArray(restoredData.weapons)){
    const restoredWeaponIndex=restoredData.weapons.findIndex(weapon=>String(weapon&&weapon.weaponId||'')===savedWeaponId);
    if(restoredWeaponIndex>=0)selectedWeaponIndex=restoredWeaponIndex+1;
  }
  selectedAbilityKey=savedAbility;
  applyActiveUnitDetails();
  syncUnitDetailVisibility();
  refreshNewViewTitleFromLegacy();
  cachedLiveViewHeader=captureNewViewHeaderSnapshot();
  hasLiveViewCache=true;
  return ok;
}
function toggleNewViewAbilityTag(key,tag){
  if(newViewProcessingLocked()||!tag||tag.locked)return false;
  const data=activeUnitIndex===null?null:unitDataByIndex[activeUnitIndex];
  const entryId=String(data&&data.entryId||'');
  const rawTag=String(tag.tag||tag.label||'').trim();
  if(!entryId||!rawTag)return false;
  let result=null;
  try{
    if(parent&&typeof parent.toggleAlternateViewAbilityTag==='function'){
      result=parent.toggleAlternateViewAbilityTag({
        entryId,
        sourceKind:String(tag.sourceKind||'ability'),
        itemKey:String(key||''),
        tag:rawTag,
        category:String(tag.category||''),
        defaultOn:tag.defaultOn!==false
      });
    }
  }catch(_){result=null}
  if(!result||!result.ok)return false;
  return refreshNewViewAfterTagMutation();
}
function toggleNewViewWeaponTag(weaponIndex,tagIndex){
  if(newViewProcessingLocked()||selectedWeaponIndex!==weaponIndex)return false;
  const data=activeUnitIndex===null?null:unitDataByIndex[activeUnitIndex];
  const weapon=data&&Array.isArray(data.weapons)?data.weapons[weaponIndex-1]:null;
  const state=weapon&&Array.isArray(weapon.tagStates)?weapon.tagStates[tagIndex]:null;
  const tag=String(state&&state.tag||weapon&&Array.isArray(weapon.tags)&&weapon.tags[tagIndex]||'').trim();
  if(!data||!weapon||!tag||state&&state.locked)return false;
  let result=null;
  try{
    if(parent&&typeof parent.toggleAlternateViewWeaponTag==='function'){
      result=parent.toggleAlternateViewWeaponTag({entryId:String(data.entryId||''),weaponKey:String(weapon.weaponId||''),tag});
    }
  }catch(_){result=null}
  if(!result||!result.ok)return false;
  return refreshNewViewAfterTagMutation();
}
function toggleBoyzNewViewWeaponTag(weaponId,tagIndex){
  if(newViewProcessingLocked())return false;
  const cleanWeaponId=normalizeBoyzWeaponId(weaponId);
  if(!cleanWeaponId||normalizeBoyzWeaponId(boyzNewViewSelectedWeaponId)!==cleanWeaponId)return false;
  const data=activeUnitIndex===null?null:unitDataByIndex[activeUnitIndex];
  const weapon=data&&Array.isArray(data.weapons)?data.weapons.find(item=>normalizeBoyzWeaponId(item&&item.weaponId)===cleanWeaponId):null;
  const state=weapon&&Array.isArray(weapon.tagStates)?weapon.tagStates[tagIndex]:null;
  const tag=String(state&&state.tag||weapon&&Array.isArray(weapon.tags)&&weapon.tags[tagIndex]||'').trim();
  if(!data||!weapon||!tag||state&&state.locked)return false;
  let result=null;
  try{
    if(parent&&typeof parent.toggleAlternateViewWeaponTag==='function'){
      result=parent.toggleAlternateViewWeaponTag({entryId:String(data.entryId||''),weaponKey:String(weapon.weaponId||''),tag});
    }
  }catch(_){result=null}
  if(!result||!result.ok)return false;
  return refreshNewViewAfterTagMutation();
}
"""
if view_np.count(old_helpers) != 1:
    raise SystemExit(f"Tag helper insertion point: expected 1 match, found {view_np.count(old_helpers)}")
view_np = view_np.replace(old_helpers, new_helpers, 1)

# Normal Weapon Tags: clickable only while their Weapon is selected; locked Tags
# remain immutable. Preserve the existing selection-based visual gate.
old_weapon_tail = """        el.dataset.tagActive=tagActive?'true':'false';
        el.dataset.tagLocked=state&&state.locked?'true':'false';
        el.dataset.weaponSelected=weaponSelected?'true':'false';
"""
new_weapon_tail = old_weapon_tail + """        el.dataset.weaponIndex=String(i);
        el.dataset.tagIndex=String(index);
        el.onclick=event=>{event.stopPropagation();toggleNewViewWeaponTag(i,index)};
"""
if view_np.count(old_weapon_tail) != 1:
    raise SystemExit(f"normal Weapon Tag binding: expected 1 match, found {view_np.count(old_weapon_tail)}")
view_np = view_np.replace(old_weapon_tail, new_weapon_tail, 1)

# Ability Tags: each badge owns the click. Ability title/description interactions
# stay independent and unchanged.
old_ability_tail = """      badge.dataset.tagActive=tagActive?'true':'false';
      badge.dataset.tagLocked=tag&&tag.locked?'true':'false';
      tags.appendChild(badge);
"""
new_ability_tail = """      badge.dataset.tagActive=tagActive?'true':'false';
      badge.dataset.tagLocked=tag&&tag.locked?'true':'false';
      badge.dataset.tagValue=String(tag&&tag.tag||tag&&tag.label||'');
      badge.dataset.tagCategory=String(tag&&tag.category||'');
      badge.dataset.tagDefaultOn=tag&&tag.defaultOn===false?'false':'true';
      badge.onclick=event=>{event.stopPropagation();toggleNewViewAbilityTag(key,tag)};
      tags.appendChild(badge);
"""
if view_np.count(old_ability_tail) != 1:
    raise SystemExit(f"Ability Tag binding: expected 1 match, found {view_np.count(old_ability_tail)}")
view_np = view_np.replace(old_ability_tail, new_ability_tail, 1)

# Boyz uses a custom Weapon renderer, so give its Tag row the same state/click
# contract instead of bypassing Phase 2.
old_boyz_tags = """function makeBoyzWeaponTags(template,weapon){
  const tags=Array.isArray(weapon.tags)?weapon.tags:[];
  if(!tags.length)return null;
  const row=template.cloneNode(true);
  row.className='weapon-tags boyz-subunit-node boyz-subunit-tags';
  row.style.display='flex';
  row.dataset.weaponId=String(weapon.weaponId||'');
  const tagEls=[...row.querySelectorAll('.weapon-tag')];
  tagEls.forEach((el,index)=>{el.textContent=String(tags[index]||'');el.style.display=tags[index]?'inline-flex':'none'});
  return row;
}
"""
new_boyz_tags = """function makeBoyzWeaponTags(template,weapon){
  const tags=Array.isArray(weapon.tags)?weapon.tags:[];
  if(!tags.length)return null;
  const row=template.cloneNode(true);
  row.className='weapon-tags boyz-subunit-node boyz-subunit-tags';
  row.style.display='flex';
  row.dataset.weaponId=String(weapon.weaponId||'');
  const tagStates=Array.isArray(weapon.tagStates)?weapon.tagStates:[];
  const weaponSelected=normalizeBoyzWeaponId(boyzNewViewSelectedWeaponId)===normalizeBoyzWeaponId(weapon.weaponId);
  const tagEls=[...row.querySelectorAll('.weapon-tag')];
  tagEls.forEach((el,index)=>{
    const label=String(tags[index]||'');
    const state=tagStates[index]||null;
    const tagActive=state?Boolean(state.active):true;
    const displayActive=weaponSelected&&tagActive;
    el.textContent=label;
    el.style.display=label?'inline-flex':'none';
    el.classList.toggle('tag-state-on',Boolean(label)&&displayActive);
    el.classList.toggle('tag-state-off',Boolean(label)&&!displayActive);
    el.classList.toggle('tag-state-locked',Boolean(label)&&Boolean(state&&state.locked));
    el.dataset.tagActive=tagActive?'true':'false';
    el.dataset.tagLocked=state&&state.locked?'true':'false';
    el.dataset.weaponSelected=weaponSelected?'true':'false';
    el.dataset.tagIndex=String(index);
    el.onclick=event=>{event.stopPropagation();toggleBoyzNewViewWeaponTag(String(weapon.weaponId||''),index)};
  });
  return row;
}
"""
if view_np.count(old_boyz_tags) != 1:
    raise SystemExit(f"Boyz Weapon Tag renderer: expected 1 match, found {view_np.count(old_boyz_tags)}")
view_np = view_np.replace(old_boyz_tags, new_boyz_tags, 1)

text = text[: vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2) :]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.143
    Scope: Unified New View Tag interaction. Ability Tags are now tappable and toggle the same per-roster Unit Tag state used by Old View; their CSV/default state remains the initial authority and their existing On/Off presentation remains unchanged. Weapon Tags are tappable only while their Weapon is selected; locked/innate Weapon Tags remain immutable and On. The custom Boyz Weapon renderer follows the same selected-Weapon and locked-Tag contract. Successful toggles persist through the existing roster library and refresh New View from the resulting roster state while preserving the open Unit and selected Weapon. New View Lock is a hard gate: locked snapshots remain inert and no Tag state write, persistence, recalculation, or refresh is started from a Tag click while locked. Ability-title Active and Short/Long description interactions remain separate from Tag state.
    Risk areas: New View Tag interaction and roster-state bridge only. No Tag palette, typography, box geometry, grid/layout, CSV data, Tag definitions, Weapon-selection rules, Probable activation policy, FIX mode, Cards, Waha, or Edit controls changed.
  -->

'''
marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.142\n"
if text.count(marker) != 1:
    raise SystemExit("V31.142 change-note insertion marker missing")
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
    "function refreshNewViewAfterTagMutation(){",
    "function toggleNewViewAbilityTag(key,tag){",
    "function toggleNewViewWeaponTag(weaponIndex,tagIndex){",
    "function toggleBoyzNewViewWeaponTag(weaponId,tagIndex){",
    "if(newViewProcessingLocked()||!tag||tag.locked)return false;",
    "if(newViewProcessingLocked()||selectedWeaponIndex!==weaponIndex)return false;",
    "badge.onclick=event=>{event.stopPropagation();toggleNewViewAbilityTag(key,tag)};",
    "el.onclick=event=>{event.stopPropagation();toggleNewViewWeaponTag(i,index)};",
    "toggleBoyzNewViewWeaponTag(String(weapon.weaponId||''),index)",
    "const displayActive=weaponSelected&&tagActive;",
]:
    if expected not in final_view:
        raise SystemExit("V31.143 View acceptance failed: " + expected)

for expected in [
    "window.toggleAlternateViewAbilityTag = function(payload = {}) {",
    "window.toggleAlternateViewWeaponTag = function(payload = {}) {",
    'persistRosterLibrary({ reason: "new-view-ability-tag", skipNoteDeleteFinalize: true });',
    'persistRosterLibrary({ reason: "new-view-weapon-tag", skipNoteDeleteFinalize: true });',
    "<title>WH40k 11th V31.143</title>",
    "The current baseline is WH40k_11th_V31.143;",
    'const APP_VERSION = "31.143";',
    "version: 'V31.143',",
    "CHANGE NOTE - WH40k_11th_V31.143",
]:
    if expected not in text:
        raise SystemExit("V31.143 release acceptance failed: " + expected)

# Phase 1 visual contracts must remain intact.
for expected in [
    ".weapon-tags .weapon-tag.tag-state-off{color:rgba(154,160,166,.5)!important;font:700 var(--meta)/1 Roboto,Arial,sans-serif!important}",
    ".unit-ability-tags .weapon-tag.ability-tag-state.tag-state-on{background:var(--btn)!important;color:var(--orange)!important;opacity:1!important}",
    "const displayActive=weaponSelected&&tagActive;",
]:
    if expected not in final_view:
        raise SystemExit("V31.143 Phase 1 regression: " + expected)

path.write_text(text, encoding="utf-8")
print("Built V31.143: New View Ability and Weapon Tags now toggle roster-backed state while unlocked")
