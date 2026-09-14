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
replace_once("<title>WH40k 11th V31.143</title>", "<title>WH40k 11th V31.144</title>", "title")
replace_once(
    "The current baseline is WH40k_11th_V31.143;",
    "The current baseline is WH40k_11th_V31.144;",
    "baseline",
)
replace_once('const APP_VERSION = "31.143";', 'const APP_VERSION = "31.144";', "APP_VERSION")
replace_once("version: 'V31.143',", "version: 'V31.144',", "quality version")

view_pat = re.compile(
    r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)',
    re.S,
)
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing")
view_np = html.unescape(vm.group(2))

# Baseline contracts from V31.143.
for required in [
    "const displayActive=weaponSelected&&tagActive;",
    "grid.querySelectorAll('.detail-box-row .detail-box').forEach(el=>{el.classList.remove('keyword-muted');el.classList.toggle('detail-row-muted',hasSelection)});",
    ".detail-core-ability{flex:0 0 auto;min-width:0;color:var(--orange)}",
    ".weapon-tags .weapon-tag.tag-state-on,.unit-ability-tags .weapon-tag.tag-state-on{background:var(--btn)!important;color:var(--orange)!important}",
    "function toggleNewViewWeaponTag(weaponIndex,tagIndex){",
    "function makeBoyzWeaponTags(template,weapon){",
]:
    if required not in view_np:
        raise SystemExit("V31.144 baseline contract missing: " + required)

# An open Unit is the active Unit. Its compact Unit-level Tags must remain fully
# active/orange even after a Weapon is selected. Do not apply the Weapon-focus
# muted class to the Unit detail boxes; clear any stale muted class instead.
old_unit_focus = "grid.querySelectorAll('.detail-box-row .detail-box').forEach(el=>{el.classList.remove('keyword-muted');el.classList.toggle('detail-row-muted',hasSelection)});"
new_unit_focus = "grid.querySelectorAll('.detail-box-row .detail-box').forEach(el=>{el.classList.remove('keyword-muted','detail-row-muted')});"
if view_np.count(old_unit_focus) != 1:
    raise SystemExit(f"Unit Tag focus rule: expected 1 match, found {view_np.count(old_unit_focus)}")
view_np = view_np.replace(old_unit_focus, new_unit_focus, 1)

# A selected Weapon is the active Weapon. Every Tag belonging to that selected
# Weapon uses the active/orange presentation at full opacity, regardless of its
# stored roster Tag toggle. The stored state remains intact in dataset/tagActive
# and the existing V31.143 click bridge is unchanged. Apply the same presentation
# rule to the custom Boyz Weapon renderer.
old_display = "const displayActive=weaponSelected&&tagActive;"
new_display = "const displayActive=weaponSelected;"
count = view_np.count(old_display)
if count != 2:
    raise SystemExit(f"Weapon Tag active presentation: expected 2 matches, found {count}")
view_np = view_np.replace(old_display, new_display)

text = text[: vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2) :]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.144
    Scope: Unified New View active Unit/Weapon Tag presentation. An opened Unit is the active Unit, so its compact Unit-level Tags remain in their existing active/orange full-opacity treatment even after a Weapon is selected; Weapon focus no longer applies the muted detail-row class to those Unit Tags. A selected Weapon is the active Weapon, so all Tags shown for that selected Weapon use the existing active/orange full-opacity presentation. The same visual rule applies to Boyz custom Weapon rows. Stored roster Tag state, Tag click/write behavior introduced in V31.143, locked/innate handling, Tag data, selection mechanics, grid/layout, typography, box geometry, and persistence remain unchanged.
    Risk areas: New View Unit-level Tag focus presentation and selected-Weapon Tag presentation only. No Ability Tag presentation, CSV data, Weapon/Unit stats, Probable, lock/FIX, Cards, Waha behavior, Edit, or persistence contract changed.
  -->

'''
marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.143\n"
if text.count(marker) != 1:
    raise SystemExit("V31.143 change-note insertion marker missing")
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
    "grid.querySelectorAll('.detail-box-row .detail-box').forEach(el=>{el.classList.remove('keyword-muted','detail-row-muted')});",
    "const displayActive=weaponSelected;",
    ".detail-core-ability{flex:0 0 auto;min-width:0;color:var(--orange)}",
    ".weapon-tags .weapon-tag.tag-state-on,.unit-ability-tags .weapon-tag.tag-state-on{background:var(--btn)!important;color:var(--orange)!important}",
    "el.classList.toggle('tag-state-on',Boolean(label)&&displayActive);",
    "el.classList.toggle('tag-state-off',Boolean(label)&&!displayActive);",
    "function toggleNewViewWeaponTag(weaponIndex,tagIndex){",
    "function toggleBoyzNewViewWeaponTag(weaponId,tagIndex){",
]:
    if expected not in final_view:
        raise SystemExit("V31.144 View acceptance failed: " + expected)

if final_view.count("const displayActive=weaponSelected;") != 2:
    raise SystemExit("V31.144 acceptance failed: normal/Boyz Weapon Tag active presentation not both updated")

for forbidden in [
    "const displayActive=weaponSelected&&tagActive;",
    "el.classList.toggle('detail-row-muted',hasSelection)",
]:
    if forbidden in final_view:
        raise SystemExit("V31.144 acceptance failed: obsolete muting rule remains: " + forbidden)

for expected in [
    "<title>WH40k 11th V31.144</title>",
    "The current baseline is WH40k_11th_V31.144;",
    'const APP_VERSION = "31.144";',
    "version: 'V31.144',",
    "CHANGE NOTE - WH40k_11th_V31.144",
]:
    if expected not in text:
        raise SystemExit("V31.144 release acceptance failed: " + expected)

path.write_text(text, encoding="utf-8")
print("Built V31.144: active Unit and selected Weapon Tags stay orange/full-opacity")
