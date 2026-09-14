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
replace_once("<title>WH40k 11th V31.136</title>", "<title>WH40k 11th V31.137</title>", "title")
replace_once(
    "The current baseline is WH40k_11th_V31.136;",
    "The current baseline is WH40k_11th_V31.137;",
    "baseline",
)
replace_once('const APP_VERSION = "31.136";', 'const APP_VERSION = "31.137";', "APP_VERSION")
replace_once("version: 'V31.136',", "version: 'V31.137',", "quality version")

view_pat = re.compile(
    r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)',
    re.S,
)
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing")
view_np = html.unescape(vm.group(2))

for required in [
    "/* V31.135 always-open Unit Ability side-detail layout in unified New View. */",
    "/* V31.136 New View focus rows follow existing muted Weapon Tags */",
    "function makeNewViewAbilityBlock(startRow,key,ability,visibleTags,active,useLong){",
    "if(visibleTags.length){",
    "description.onclick=event=>{event.stopPropagation();toggleNewViewAbilityDescription(key)};",
    "function applyViewWeaponTagFocus(){",
]:
    if required not in view_np:
        raise SystemExit("V31.137 baseline contract missing: " + required)

# Replace only the V31.135 Ability presentation CSS. Behavior/data stay intact.
css_start = view_np.find("/* V31.135 always-open Unit Ability side-detail layout in unified New View. */")
css_end_marker = ".unit-ability-tags .weapon-tag{height:auto;min-height:var(--std);max-width:100%;white-space:normal;overflow:visible;text-align:center;line-height:1.1;padding-top:4px;padding-bottom:4px}"
css_end = view_np.find(css_end_marker, css_start)
if css_start < 0 or css_end < 0:
    raise SystemExit("V31.135 Ability CSS bounds missing")
css_end += len(css_end_marker)

new_css = r'''/* V31.137 Ability description layout/color fixes in unified New View. */
.unit-ability-block{grid-column:1/span 16;z-index:4;box-sizing:border-box;align-self:start;display:grid;grid-template-columns:repeat(16,var(--cell));align-items:stretch;min-width:0;min-height:calc(var(--cell)*2);background:transparent;overflow:visible}
.unit-ability-button{grid-column:1/span 5;grid-row:1;box-sizing:border-box;align-self:stretch;min-width:0;min-height:calc(var(--cell)*2);height:auto;display:flex;align-items:center;justify-content:center;text-align:center;padding:4px 8px;white-space:normal;overflow:hidden;overflow-wrap:anywhere;background:var(--card);border:1px solid var(--border);border-radius:4px;color:rgba(241,243,244,.5);font:900 var(--body)/1 Roboto,Arial,sans-serif;cursor:pointer}
.unit-ability-button.ability-active{color:#80d6a3!important}
.unit-ability-detail{grid-column:6/span 11;grid-row:1;box-sizing:border-box;align-self:stretch;height:100%;min-width:0;display:flex;flex-direction:column;align-items:stretch;background:transparent;overflow:visible}
.unit-ability-description-row{box-sizing:border-box;width:100%;min-width:0;min-height:calc(var(--cell)*2);flex:1 1 auto;display:flex;align-items:center;padding:4px 8px;white-space:pre-line;overflow:visible;overflow-wrap:anywhere;background:var(--card);border:1px solid var(--border);border-radius:4px;color:rgba(241,243,244,.5);font:700 var(--meta)/1.25 Roboto,Arial,sans-serif;cursor:pointer}
.unit-ability-block.ability-active .unit-ability-description-row{color:#80d6a3!important}
.unit-ability-tags{box-sizing:border-box;width:100%;min-width:0;min-height:var(--cell);flex:0 0 auto;display:flex;flex-wrap:wrap;align-items:center;align-content:center;justify-content:flex-start;gap:var(--gap);padding:1px 0;overflow:visible;background:transparent}
.unit-ability-tags .weapon-tag{height:auto;min-height:var(--std);max-width:100%;white-space:normal;overflow:visible;text-align:center;line-height:1.1;padding-top:4px;padding-bottom:4px}'''
view_np = view_np[:css_start] + new_css + view_np[css_end:]

# No Tag element is created at all when there are no visible Tags. The stretched
# detail/description now fills the rounded grid height, eliminating the phantom
# blank row while preserving the fixed outer grid.

text = text[: vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2) :]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.137
    Scope: Fix unified New View Ability description presentation. Ability descriptions now preserve authored line breaks with white-space:pre-line while continuing to wrap normally. When an Ability has no visible Tags, no Tag element/row is created and the Description fills the full F-P height of the Ability block, eliminating the blank phantom Tag row. When Tags are present, the Description plus actual Tags fill the right side and the A-E title continues to stretch to their combined height. Short and Long descriptions now follow the exact title Active/Inactive color state: muted gray when inactive and green when active. Short/Long toggling remains independent from Active state. V31.136 focus-row/muted-Tag presentation and all Weapon selection behavior remain unchanged.
    Risk areas: Unified New View Ability presentation only. No Ability data/order/filter semantics, Old Edit authority, Weapon/Tag state behavior, Boyz data, Unit stats, Probable, lock/FIX, Cards, Waha, CSV data, persistence, or Version controls changed.
  -->

'''
marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.136\n"
if text.count(marker) != 1:
    raise SystemExit("V31.136 change-note insertion marker missing")
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
    "/* V31.137 Ability description layout/color fixes in unified New View. */",
    "/* V31.136 New View focus rows follow existing muted Weapon Tags */",
    ".unit-ability-detail{grid-column:6/span 11;grid-row:1;box-sizing:border-box;align-self:stretch;height:100%;",
    "white-space:pre-line;",
    "color:rgba(241,243,244,.5);font:700 var(--meta)/1.25 Roboto,Arial,sans-serif",
    ".unit-ability-block.ability-active .unit-ability-description-row{color:#80d6a3!important}",
    ".unit-ability-tags{box-sizing:border-box;width:100%;min-width:0;min-height:var(--cell);flex:0 0 auto;",
    "if(visibleTags.length){",
    "description.onclick=event=>{event.stopPropagation();toggleNewViewAbilityDescription(key)};",
    "button.onclick=event=>{event.stopPropagation();toggleNewViewAbilityActive(key)};",
    "function applyViewWeaponTagFocus(){",
]:
    if expected not in final_view:
        raise SystemExit("V31.137 View acceptance failed: " + expected)

for forbidden in [
    "/* V31.135 always-open Unit Ability side-detail layout in unified New View. */",
    ".unit-ability-description-row{box-sizing:border-box;width:100%;min-width:0;min-height:calc(var(--cell)*2);display:flex;align-items:center;padding:4px 8px;white-space:normal;",
    ".unit-ability-description-row{box-sizing:border-box;width:100%;min-width:0;min-height:calc(var(--cell)*2);flex:1 1 auto;display:flex;align-items:center;padding:4px 8px;white-space:normal;",
    "color:var(--secondary);font:700 var(--meta)/1.25 Roboto,Arial,sans-serif",
]:
    if forbidden in final_view:
        raise SystemExit("V31.137 acceptance failed: old Ability description presentation remains: " + forbidden)

for expected in [
    "<title>WH40k 11th V31.137</title>",
    "The current baseline is WH40k_11th_V31.137;",
    'const APP_VERSION = "31.137";',
    "version: 'V31.137',",
    "CHANGE NOTE - WH40k_11th_V31.137",
]:
    if expected not in text:
        raise SystemExit("V31.137 release acceptance failed: " + expected)

path.write_text(text, encoding="utf-8")
print("Built V31.137: Ability line breaks, no phantom no-Tag row, and description Active/Inactive color parity")
