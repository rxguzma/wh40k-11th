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
replace_once("<title>WH40k 11th V31.140</title>", "<title>WH40k 11th V31.141</title>", "title")
replace_once(
    "The current baseline is WH40k_11th_V31.140;",
    "The current baseline is WH40k_11th_V31.141;",
    "baseline",
)
replace_once('const APP_VERSION = "31.140";', 'const APP_VERSION = "31.141";', "APP_VERSION")
replace_once("version: 'V31.140',", "version: 'V31.141',", "quality version")

view_pat = re.compile(
    r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)',
    re.S,
)
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing")
view_np = html.unescape(vm.group(2))

for required in [
    "/* V31.138 roster-backed Tag state display in unified New View. */",
    "/* V31.140 Ability Tag state outranks Weapon-selection muting. */",
    ".weapon-tags .weapon-tag.tag-state-off,.unit-ability-tags .weapon-tag.tag-state-off{background:rgba(154,160,166,.5)!important;color:var(--muted)!important}",
    ".unit-ability-tags .weapon-tag.ability-tag-state.tag-state-off{background:rgba(154,160,166,.5)!important;color:var(--muted)!important;opacity:1!important}",
    "const weaponSelected=selectedWeaponIndex===i;",
    "const displayActive=weaponSelected&&tagActive;",
]:
    if required not in view_np:
        raise SystemExit("V31.141 baseline contract missing: " + required)

# Restore the exact V31.132 muted-Tag visual contract: muting changes only the
# Tag text color. The Tag box keeps its normal/base background and border.
# V31.139 Weapon-selection gating and V31.140 Ability Tag state precedence stay intact.
replace_from = ".weapon-tags .weapon-tag.tag-state-off,.unit-ability-tags .weapon-tag.tag-state-off{background:rgba(154,160,166,.5)!important;color:var(--muted)!important}"
replace_to = ".weapon-tags .weapon-tag.tag-state-off,.unit-ability-tags .weapon-tag.tag-state-off{color:var(--muted)!important}"
if view_np.count(replace_from) != 1:
    raise SystemExit(f"general muted Tag palette: expected 1 match, found {view_np.count(replace_from)}")
view_np = view_np.replace(replace_from, replace_to, 1)

ability_from = ".unit-ability-tags .weapon-tag.ability-tag-state.tag-state-off{background:rgba(154,160,166,.5)!important;color:var(--muted)!important;opacity:1!important}"
ability_to = ".unit-ability-tags .weapon-tag.ability-tag-state.tag-state-off{color:var(--muted)!important;opacity:1!important}"
if view_np.count(ability_from) != 1:
    raise SystemExit(f"Ability muted Tag palette: expected 1 match, found {view_np.count(ability_from)}")
view_np = view_np.replace(ability_from, ability_to, 1)

text = text[: vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2) :]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.141
    Scope: Unified New View muted Tag colors only. Restore the V31.132 muted Tag treatment: a muted Tag changes only to the existing muted text color while retaining the normal Tag box background/border. Remove the later rgba(154,160,166,.5) fill from muted Weapon and Ability Tag boxes. Active/orange Tag styling is unchanged. V31.139 remains authoritative for Weapon Tags staying muted until their Weapon is selected; V31.140 Ability Tag state precedence is unchanged. Focus/header separator rows, grid/layout, sizing, filters, Tag data, persistence, calculations, and behavior remain unchanged.
    Risk areas: Unified New View muted Tag palette only. No Tag state logic, Weapon selection, Ability behavior, CSV data, Probable, lock/FIX, Boyz data, Cards, Waha, Edit, or persistence behavior changed.
  -->

'''
marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.140\n"
if text.count(marker) != 1:
    raise SystemExit("V31.140 change-note insertion marker missing")
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
    ".weapon-tags .weapon-tag.tag-state-off,.unit-ability-tags .weapon-tag.tag-state-off{color:var(--muted)!important}",
    ".unit-ability-tags .weapon-tag.ability-tag-state.tag-state-off{color:var(--muted)!important;opacity:1!important}",
    ".weapon-tags.weapon-muted .weapon-tag{color:var(--muted)}",
    ".weapon-tags .weapon-tag.tag-state-on,.unit-ability-tags .weapon-tag.tag-state-on{background:var(--btn)!important;color:var(--orange)!important}",
    "const weaponSelected=selectedWeaponIndex===i;",
    "const displayActive=weaponSelected&&tagActive;",
    "el.classList.toggle('tag-state-on',Boolean(label)&&displayActive);",
    "el.classList.toggle('tag-state-off',Boolean(label)&&!displayActive);",
    "/* V31.140 Ability Tag state outranks Weapon-selection muting. */",
]:
    if expected not in final_view:
        raise SystemExit("V31.141 View acceptance failed: " + expected)

for forbidden in [
    ".weapon-tags .weapon-tag.tag-state-off,.unit-ability-tags .weapon-tag.tag-state-off{background:rgba(154,160,166,.5)",
    ".unit-ability-tags .weapon-tag.ability-tag-state.tag-state-off{background:rgba(154,160,166,.5)",
]:
    if forbidden in final_view:
        raise SystemExit("V31.141 acceptance failed: later gray muted-Tag fill remains")

for expected in [
    "<title>WH40k 11th V31.141</title>",
    "The current baseline is WH40k_11th_V31.141;",
    'const APP_VERSION = "31.141";',
    "version: 'V31.141',",
    "CHANGE NOTE - WH40k_11th_V31.141",
]:
    if expected not in text:
        raise SystemExit("V31.141 release acceptance failed: " + expected)

path.write_text(text, encoding="utf-8")
print("Built V31.141: restored V31.132 muted Tag colors")
