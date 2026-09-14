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
replace_once("<title>WH40k 11th V31.137</title>", "<title>WH40k 11th V31.138</title>", "title")
replace_once(
    "The current baseline is WH40k_11th_V31.137;",
    "The current baseline is WH40k_11th_V31.138;",
    "baseline",
)
replace_once('const APP_VERSION = "31.137";', 'const APP_VERSION = "31.138";', "APP_VERSION")
replace_once("version: 'V31.137',", "version: 'V31.138',", "quality version")

# Phase 1: expose the existing roster-backed Ability Tag state to New View.
old_ability_tags = '''              const tags = getAbilityProtectedModifierTagAssignments(effectiveItem).map(assignment => {
                const definition = getTagDefinitionByTagAndCategory(assignment.tag, assignment.category);
                if (isPromotedUnitLevelTag(assignment.tag, definition)) return null;
                return {
                  label: getAbilityTagDisplayLabel(assignment.tag),
                  category: String(assignment.category || ""),
                  scope: getTagDefinitionWeaponScope(definition, assignment.category).kind
                };
              }).filter(Boolean);'''
new_ability_tags = '''              const defaultTagsOn = getRosterTaggedSourceDefaultActive("ability", sourceItem);
              const tags = getAbilityProtectedModifierTagAssignments(effectiveItem).map(assignment => {
                const definition = getTagDefinitionByTagAndCategory(assignment.tag, assignment.category);
                if (isPromotedUnitLevelTag(assignment.tag, definition)) return null;
                return {
                  label: getAbilityTagDisplayLabel(assignment.tag),
                  tag: String(assignment.tag || ""),
                  category: String(assignment.category || ""),
                  scope: getTagDefinitionWeaponScope(definition, assignment.category).kind,
                  defaultOn: Boolean(defaultTagsOn),
                  active: getRosterEntryAbilityTagState(entry, sourceItem, assignment.tag, defaultTagsOn, assignment.category),
                  locked: false
                };
              }).filter(Boolean);'''
replace_once(old_ability_tags, new_ability_tags, "New View Ability Tag state bridge")

# Phase 1: expose the existing roster-backed Weapon Tag state to New View.
old_weapon_map = '''        weapons: weapons.map(weapon => {
          const range = String(weapon.range ?? "").trim();
          const melee = range === "-" || range.toLowerCase() === "melee" || /\\(melee\\)/i.test(String(weapon.name || ""));
          const scope = melee ? "MELEE" : (range ? "SHOOT" : "OTHER");
          return {
            weaponId: String(weapon.weaponId || ""),
            quantity: entry && unit ? getRosterWeaponQuantity(entry, unit, weapon) : 0,
            name: String(weapon.name || weapon.weaponId || ""),
            range,
            attacks: String(weapon.attacks ?? ""),
            skill: String(weapon.skill ?? ""),
            strength: String(weapon.strength ?? ""),
            ap: String(weapon.ap ?? ""),
            damage: String(weapon.damage ?? ""),
            tags: splitWeaponAbilities(weapon.weaponAbility),
            scope
          };
        })'''
new_weapon_map = '''        weapons: weapons.map(weapon => {
          const range = String(weapon.range ?? "").trim();
          const melee = range === "-" || range.toLowerCase() === "melee" || /\\(melee\\)/i.test(String(weapon.name || ""));
          const scope = melee ? "MELEE" : (range ? "SHOOT" : "OTHER");
          const tags = splitWeaponAbilities(weapon.weaponAbility);
          const tagStates = tags.map(tag => {
            const locked = isInnateWeaponAbilityTag(weapon, tag);
            return {
              tag: String(tag || ""),
              active: locked ? true : getRosterEntryWeaponTagState(entry, weapon, tag, true),
              locked: Boolean(locked)
            };
          });
          return {
            weaponId: String(weapon.weaponId || ""),
            quantity: entry && unit ? getRosterWeaponQuantity(entry, unit, weapon) : 0,
            name: String(weapon.name || weapon.weaponId || ""),
            range,
            attacks: String(weapon.attacks ?? ""),
            skill: String(weapon.skill ?? ""),
            strength: String(weapon.strength ?? ""),
            ap: String(weapon.ap ?? ""),
            damage: String(weapon.damage ?? ""),
            tags,
            tagStates,
            scope
          };
        })'''
replace_once(old_weapon_map, new_weapon_map, "New View Weapon Tag state bridge")

# Patch the embedded unified New View presentation only. No click behavior is added.
view_pat = re.compile(
    r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)',
    re.S,
)
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing")
view_np = html.unescape(vm.group(2))

for required in [
    "/* V31.137 Ability description layout/color fixes in unified New View. */",
    "/* V31.136 New View focus rows follow existing muted Weapon Tags */",
    "function makeNewViewAbilityBlock(startRow,key,ability,visibleTags,active,useLong){",
    "badge.className='weapon-tag';",
    "const tagRow=grid.querySelector('.weapon-tags-'+i);",
    "tagEls.forEach((el,index)=>{el.textContent=String(tags[index]||'');el.style.display=tags[index]?'inline-flex':'none'});",
]:
    if required not in view_np:
        raise SystemExit("V31.138 baseline contract missing: " + required)

# Use the existing New View Tag colors/boxes for real roster Tag state. Keep all
# dimensions, wrapping, borders, grid placement, and selection geometry intact.
state_css = r'''

/* V31.138 roster-backed Tag state display in unified New View. */
.weapon-tags .weapon-tag.tag-state-on,.unit-ability-tags .weapon-tag.tag-state-on{background:var(--btn)!important;color:var(--orange)!important}
.weapon-tags .weapon-tag.tag-state-off,.unit-ability-tags .weapon-tag.tag-state-off{background:rgba(154,160,166,.5)!important;color:var(--muted)!important}
'''
css_marker = "/* V31.136 New View focus rows follow existing muted Weapon Tags */"
if view_np.count(css_marker) != 1:
    raise SystemExit("V31.136 New View focus-row CSS marker missing")
view_np = view_np.replace(css_marker, state_css + "\n" + css_marker, 1)

# Ability Tags remain non-clickable in Phase 1; only their real state is rendered.
old_ability_badge = '''      const badge=document.createElement('span');
      badge.className='weapon-tag';
      badge.textContent=String(tag&&tag.label||'');
      tags.appendChild(badge);'''
new_ability_badge = '''      const badge=document.createElement('span');
      const tagActive=Boolean(tag&&tag.active);
      badge.className='weapon-tag '+(tagActive?'tag-state-on':'tag-state-off')+(tag&&tag.locked?' tag-state-locked':'');
      badge.textContent=String(tag&&tag.label||'');
      badge.dataset.tagActive=tagActive?'true':'false';
      badge.dataset.tagLocked=tag&&tag.locked?'true':'false';
      tags.appendChild(badge);'''
if view_np.count(old_ability_badge) != 1:
    raise SystemExit(f"Ability Tag badge renderer: expected 1 match, found {view_np.count(old_ability_badge)}")
view_np = view_np.replace(old_ability_badge, new_ability_badge, 1)

# Weapon Tags remain non-clickable in Phase 1; preserve the existing rows and
# focus behavior while applying each Tag's roster-backed active/locked state.
old_weapon_refresh = '''    if(tagRow){
      const tags=weapon&&Array.isArray(weapon.tags)?weapon.tags:[];
      tagRow.dataset.liveAvailable=tags.length?'true':'false';
      const tagEls=[...tagRow.querySelectorAll('.weapon-tag')];
      tagEls.forEach((el,index)=>{el.textContent=String(tags[index]||'');el.style.display=tags[index]?'inline-flex':'none'});
    }'''
new_weapon_refresh = '''    if(tagRow){
      const tags=weapon&&Array.isArray(weapon.tags)?weapon.tags:[];
      const tagStates=weapon&&Array.isArray(weapon.tagStates)?weapon.tagStates:[];
      tagRow.dataset.liveAvailable=tags.length?'true':'false';
      const tagEls=[...tagRow.querySelectorAll('.weapon-tag')];
      tagEls.forEach((el,index)=>{
        const label=String(tags[index]||'');
        const state=tagStates[index]||null;
        const tagActive=state?Boolean(state.active):true;
        el.textContent=label;
        el.style.display=label?'inline-flex':'none';
        el.classList.toggle('tag-state-on',Boolean(label)&&tagActive);
        el.classList.toggle('tag-state-off',Boolean(label)&&!tagActive);
        el.classList.toggle('tag-state-locked',Boolean(label)&&Boolean(state&&state.locked));
        el.dataset.tagActive=tagActive?'true':'false';
        el.dataset.tagLocked=state&&state.locked?'true':'false';
      });
    }'''
if view_np.count(old_weapon_refresh) != 1:
    raise SystemExit(f"Weapon Tag refresh renderer: expected 1 match, found {view_np.count(old_weapon_refresh)}")
view_np = view_np.replace(old_weapon_refresh, new_weapon_refresh, 1)

text = text[: vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2) :]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.138
    Scope: Phase 1 of Old View-style Tag behavior in unified New View: state/display only. New View now receives the existing roster-backed state for each visible Ability Tag, including the CSV-driven Default_Active fallback and any saved per-Unit override, and renders On Tags with the existing active Tag treatment and Off Tags with the existing muted Tag treatment. Visible Weapon Tags also receive their existing roster-backed state and locked/innate status; locked Tags remain displayed On. This phase adds no Tag click handlers and performs no Tag state writes, persistence changes, or new recalculation path. Ability-title Active state remains separate from Tag state. Existing New View lock, grid/layout, wrapping, sizing, filters, Weapon selection/focus, and all calculations remain unchanged.
    Risk areas: Unified New View Tag state data bridge and visual state only. No Tag interaction, CSV data, roster mutation, Unit/Weapon calculations, Probable execution, Ability-title behavior, lock/FIX, Boyz data, Cards, Waha, Edit, or persistence behavior changed.
  -->

'''
marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.137\n"
if text.count(marker) != 1:
    raise SystemExit("V31.137 change-note insertion marker missing")
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
    "/* V31.138 roster-backed Tag state display in unified New View. */",
    ".weapon-tags .weapon-tag.tag-state-on,.unit-ability-tags .weapon-tag.tag-state-on",
    ".weapon-tags .weapon-tag.tag-state-off,.unit-ability-tags .weapon-tag.tag-state-off",
    "const tagActive=Boolean(tag&&tag.active);",
    "const tagStates=weapon&&Array.isArray(weapon.tagStates)?weapon.tagStates:[];",
    "el.classList.toggle('tag-state-on',Boolean(label)&&tagActive);",
    "el.classList.toggle('tag-state-off',Boolean(label)&&!tagActive);",
    "function makeNewViewAbilityBlock(startRow,key,ability,visibleTags,active,useLong){",
    "function newViewProcessingLocked(){return Boolean(newViewHeaderLocked&&activePageMode==='view')}",
]:
    if expected not in final_view:
        raise SystemExit("V31.138 View acceptance failed: " + expected)

for forbidden in [
    "onclick=\"toggleNewViewTag",
    "toggleNewViewAbilityTag",
    "toggleNewViewWeaponTag",
]:
    if forbidden in final_view:
        raise SystemExit("V31.138 Phase 1 acceptance failed: Tag click behavior was introduced")

for expected in [
    "const defaultTagsOn = getRosterTaggedSourceDefaultActive(\"ability\", sourceItem);",
    "active: getRosterEntryAbilityTagState(entry, sourceItem, assignment.tag, defaultTagsOn, assignment.category)",
    "const tagStates = tags.map(tag => {",
    "active: locked ? true : getRosterEntryWeaponTagState(entry, weapon, tag, true)",
    "locked: Boolean(locked)",
    "<title>WH40k 11th V31.138</title>",
    "The current baseline is WH40k_11th_V31.138;",
    'const APP_VERSION = "31.138";',
    "version: 'V31.138',",
    "CHANGE NOTE - WH40k_11th_V31.138",
]:
    if expected not in text:
        raise SystemExit("V31.138 release acceptance failed: " + expected)

path.write_text(text, encoding="utf-8")
print("Built V31.138: New View now displays real roster-backed Tag On/Off/locked state; no Tag clicks added")
