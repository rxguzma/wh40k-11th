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
replace_once("<title>WH40k 11th V31.131</title>", "<title>WH40k 11th V31.132</title>", "title")
replace_once(
    "The current baseline is WH40k_11th_V31.131;",
    "The current baseline is WH40k_11th_V31.132;",
    "baseline",
)
replace_once('const APP_VERSION = "31.131";', 'const APP_VERSION = "31.132";', "APP_VERSION")
replace_once("version: 'V31.131',", "version: 'V31.132',", "quality version")

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


# Preserve V31.131 Weapon Tag focus and change only the approved Ability
# presentation/state plus the open-Unit separator color.
for required in [
    "/* V31.129 compact Unit Ability buttons in unified New View. */",
    "function restoreViewWeaponTagFocus(){",
    "function applyViewWeaponTagFocus(){",
    "function selectNewViewAbility(key){",
    "function makeNewViewAbilityBlock(startRow,laneStart,key,ability,visibleTags,active){",
    "function renderNewViewAbilitiesAndReflow(){",
    ".view-focus-separator{grid-column:1/span 16;",
]:
    if required not in view_np:
        raise SystemExit("V31.132 baseline contract missing: " + required)

# ---------------------------------------------------------------------------
# Ability title typography/state: use the same standard muted title treatment
# as New View names (Roboto 900, body size, line-height 1, 50% text color).
# Open Ability titles keep the existing active green state.
# ---------------------------------------------------------------------------
view_replace_once(
    ".unit-ability-button{grid-column:1/span 5;grid-row:1/span 2;box-sizing:border-box;min-width:0;min-height:calc(var(--cell)*2);display:flex;align-items:center;justify-content:center;text-align:center;padding:4px 8px;white-space:normal;overflow:hidden;overflow-wrap:anywhere;background:var(--card);border:1px solid var(--border);border-radius:4px;color:var(--text);font:900 var(--body)/1.05 Roboto,Arial,sans-serif;cursor:pointer}",
    ".unit-ability-button{grid-column:1/span 4;grid-row:1/span 2;box-sizing:border-box;min-width:0;min-height:calc(var(--cell)*2);display:flex;align-items:center;justify-content:center;text-align:center;padding:4px 8px;white-space:normal;overflow:hidden;overflow-wrap:anywhere;background:var(--card);border:1px solid var(--border);border-radius:4px;color:rgba(241,243,244,.5);font:900 var(--body)/1 Roboto,Arial,sans-serif;cursor:pointer}",
    "Ability button standard muted title style and four-column width",
)

# ---------------------------------------------------------------------------
# Four Ability boxes across the 16-column grid. Each remains two grid rows tall
# while collapsed. Description and Tags stay in the same four-column lane.
# ---------------------------------------------------------------------------
view_replace_once(
    ".unit-ability-block{z-index:4;box-sizing:border-box;align-self:start;display:grid;grid-template-columns:repeat(5,var(--cell));grid-template-rows:repeat(2,var(--cell));align-content:start;min-width:0;background:transparent;overflow:visible}",
    ".unit-ability-block{z-index:4;box-sizing:border-box;align-self:start;display:grid;grid-template-columns:repeat(4,var(--cell));grid-template-rows:repeat(2,var(--cell));align-content:start;min-width:0;background:transparent;overflow:visible}",
    "Ability block four-column grid",
)
view_replace_once(
    ".unit-ability-description-row{grid-column:1/span 5;grid-row:3;",
    ".unit-ability-description-row{grid-column:1/span 4;grid-row:3;",
    "Ability description four-column width",
)
view_replace_once(
    ".unit-ability-tags{grid-column:1/span 5;grid-row:4;",
    ".unit-ability-tags{grid-column:1/span 4;grid-row:4;",
    "Ability Tags four-column width",
)
view_replace_once(
    "block.style.gridColumn=String(laneStart)+' / span 5';",
    "block.style.gridColumn=String(laneStart)+' / span 4';",
    "Ability block lane span",
)
view_replace_once(
    "for(let i=0;i<abilities.length;i+=3){",
    "for(let i=0;i<abilities.length;i+=4){",
    "Ability group count",
)
view_replace_once(
    "const group=abilities.slice(i,i+3);",
    "const group=abilities.slice(i,i+4);",
    "Ability group slice",
)
view_replace_once(
    "const laneStart=1+(slot*5);",
    "const laneStart=1+(slot*4);",
    "Ability lane start",
)

# ---------------------------------------------------------------------------
# Persistent expansion state: opening one Ability no longer closes any other
# open Ability. Each Ability remains open until that same Ability is tapped
# again. This is transient View state only; it does not modify Old Edit or CSV.
# ---------------------------------------------------------------------------
view_replace_once(
    "let selectedAbilityKey=null;",
    "let selectedAbilityKey=null;\nconst openAbilityKeys=new Set();",
    "persistent Ability state declaration",
)
old_select = r'''function selectNewViewAbility(key){
  const clean=String(key||'');
  selectedWeaponIndex=null;
  selectedAbilityKey=selectedAbilityKey===clean?null:clean;
  syncWeaponLayout();
}'''
new_select = r'''function newViewAbilityOpenToken(key){
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
}'''
view_replace_once(old_select, new_select, "persistent Ability toggle")
view_replace_once(
    "const active=Boolean(key&&String(selectedAbilityKey)===key);",
    "const active=Boolean(key&&newViewAbilityIsOpen(key));",
    "Ability open-state render",
)

# ---------------------------------------------------------------------------
# Unit top/bottom focus separator rows: use the same lighter muted Tag gray.
# ---------------------------------------------------------------------------
view_replace_once(
    ".view-focus-separator{grid-column:1/span 16;height:var(--cell);align-self:stretch;justify-self:stretch;background:var(--card);border:1px solid var(--border);border-radius:4px;box-sizing:border-box;pointer-events:none;z-index:7}",
    ".view-focus-separator{grid-column:1/span 16;height:var(--cell);align-self:stretch;justify-self:stretch;background:rgba(154,160,166,.5);border:1px solid var(--border);border-radius:4px;box-sizing:border-box;pointer-events:none;z-index:7}",
    "muted Tag gray focus separators",
)

text = text[: vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2) :]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.132
    Scope: Refine unified New View Unit Ability controls. Ability titles now use the standard muted New View title typography/state: Roboto 900 at body size with line-height 1 and the existing 50% muted text color, while open Ability titles retain the existing green active state. Ability boxes are four grid columns wide, allowing four boxes across the 16-column grid, and remain two rows tall while collapsed. Ability expansion state is now independent per Ability and per Unit: opening another Ability no longer closes an already-open Ability, and each Short Description/Tag area remains open until that same Ability is tapped closed. The existing one-row gap after Weapons is retained. The full-width focus separator rows above and below the opened Unit now use the existing muted Tag gray rgba(154,160,166,.5) instead of the darker card gray.
    Risk areas: Unified New View Ability presentation/transient expansion state and focus-separator color only. V31.131 Weapon Tag focus, Ability data/order/filtering and Old Edit authority, Weapon/Boyz rendering, Unit stats, Probable, lock/FIX, Cards, Waha, CSV data, persistence, and Version controls remain unchanged.
  -->

'''
marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.131\n"
if text.count(marker) != 1:
    raise SystemExit("V31.131 change-note insertion marker missing")
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
    "grid-template-columns:repeat(4,var(--cell))",
    ".unit-ability-button{grid-column:1/span 4;grid-row:1/span 2;",
    "color:rgba(241,243,244,.5);font:900 var(--body)/1 Roboto,Arial,sans-serif",
    ".unit-ability-description-row{grid-column:1/span 4;grid-row:3;",
    ".unit-ability-tags{grid-column:1/span 4;grid-row:4;",
    "block.style.gridColumn=String(laneStart)+' / span 4';",
    "for(let i=0;i<abilities.length;i+=4){",
    "const group=abilities.slice(i,i+4);",
    "const laneStart=1+(slot*4);",
    "const openAbilityKeys=new Set();",
    "function newViewAbilityOpenToken(key){",
    "function newViewAbilityIsOpen(key){",
    "openAbilityKeys.add(token);",
    "openAbilityKeys.delete(token);",
    "const active=Boolean(key&&newViewAbilityIsOpen(key));",
    "background:rgba(154,160,166,.5);border:1px solid var(--border);",
    "function applyViewWeaponTagFocus(){",
]:
    if expected not in final_view:
        raise SystemExit("V31.132 View acceptance failed: " + expected)

for forbidden in [
    "grid-template-columns:repeat(5,var(--cell))",
    ".unit-ability-button{grid-column:1/span 5;",
    "for(let i=0;i<abilities.length;i+=3){",
    "const laneStart=1+(slot*5);",
    "const active=Boolean(key&&String(selectedAbilityKey)===key);",
]:
    if forbidden in final_view:
        raise SystemExit("V31.132 acceptance failed: old Ability geometry/state remains: " + forbidden)

for expected in [
    "<title>WH40k 11th V31.132</title>",
    "The current baseline is WH40k_11th_V31.132;",
    'const APP_VERSION = "31.132";',
    "version: 'V31.132',",
    "CHANGE NOTE - WH40k_11th_V31.132",
]:
    if expected not in text:
        raise SystemExit("V31.132 release acceptance failed: " + expected)

path.write_text(text, encoding="utf-8")
print("Built V31.132: four-column persistent Ability boxes and muted Tag-gray Unit separators")
