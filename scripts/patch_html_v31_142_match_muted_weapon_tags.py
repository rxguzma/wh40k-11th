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
replace_once("<title>WH40k 11th V31.141</title>", "<title>WH40k 11th V31.142</title>", "title")
replace_once(
    "The current baseline is WH40k_11th_V31.141;",
    "The current baseline is WH40k_11th_V31.142;",
    "baseline",
)
replace_once('const APP_VERSION = "31.141";', 'const APP_VERSION = "31.142";', "APP_VERSION")
replace_once("version: 'V31.141',", "version: 'V31.142',", "quality version")

view_pat = re.compile(
    r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)',
    re.S,
)
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing")
view_np = html.unescape(vm.group(2))

for required in [
    ".weapon-tag{height:var(--std);flex:0 0 auto;padding:0 8px;border:1px solid var(--btnborder);display:inline-flex;align-items:center;justify-content:center;border-radius:var(--radius);background:var(--btn);color:var(--orange);font:700 var(--meta)/1 Roboto,Arial,sans-serif;white-space:nowrap;overflow:hidden}",
    ".detail-box{height:var(--std);padding:0 8px;border:1px solid var(--btnborder);border-radius:var(--radius);background:var(--btn);color:var(--text);font:700 var(--meta)/1 Roboto,Arial,sans-serif;display:inline-flex;align-items:center;justify-content:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
    ".weapon-tags.weapon-muted .weapon-tag{color:rgba(154,160,166,.5)!important}",
    ".weapon-tags .weapon-tag.tag-state-off,.unit-ability-tags .weapon-tag.tag-state-off{color:var(--muted)!important}",
    "const weaponSelected=selectedWeaponIndex===i;",
    "const displayActive=weaponSelected&&tagActive;",
]:
    if required not in view_np:
        raise SystemExit("V31.142 baseline contract missing: " + required)

# Muted Weapon Tags must visually match the compact muted boxes above the
# Weapon table (for example FNP/Waha): same 700/meta typography and the exact
# V31.132 half-alpha muted text. Do not alter Ability Tags or active Tags.
old_state = ".weapon-tags .weapon-tag.tag-state-off,.unit-ability-tags .weapon-tag.tag-state-off{color:var(--muted)!important}"
new_state = """.weapon-tags .weapon-tag.tag-state-off{color:rgba(154,160,166,.5)!important;font:700 var(--meta)/1 Roboto,Arial,sans-serif!important}\n.unit-ability-tags .weapon-tag.tag-state-off{color:var(--muted)!important}"""
if view_np.count(old_state) != 1:
    raise SystemExit(f"muted Tag state rule: expected 1 match, found {view_np.count(old_state)}")
view_np = view_np.replace(old_state, new_state, 1)

text = text[: vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2) :]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.142
    Scope: Unified New View muted Weapon Tag presentation only. Muted Weapon Tags now use the exact V31.132 muted text color rgba(154,160,166,.5) and explicitly use the same 700-weight meta-size Roboto typography as the compact FNP/Waha boxes above the Weapon table. Their normal Tag background, border, dimensions, spacing, wrapping, and row geometry are unchanged. Active/orange Weapon Tag styling is unchanged, and V31.139 selection gating remains authoritative: Weapon Tags stay muted until their Weapon is selected. Ability Tag presentation/state is unchanged.
    Risk areas: Unified New View muted Weapon Tag text color/typography only. No Tag data/state writes, Weapon selection, Ability behavior, CSV data, Probable, grid/layout, lock/FIX, Boyz data, Cards, Waha behavior, Edit, or persistence behavior changed.
  -->

'''
marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.141\n"
if text.count(marker) != 1:
    raise SystemExit("V31.141 change-note insertion marker missing")
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
    ".weapon-tags .weapon-tag.tag-state-off{color:rgba(154,160,166,.5)!important;font:700 var(--meta)/1 Roboto,Arial,sans-serif!important}",
    ".unit-ability-tags .weapon-tag.tag-state-off{color:var(--muted)!important}",
    ".weapon-tags.weapon-muted .weapon-tag{color:rgba(154,160,166,.5)!important}",
    ".weapon-tags .weapon-tag.tag-state-on,.unit-ability-tags .weapon-tag.tag-state-on{background:var(--btn)!important;color:var(--orange)!important}",
    "const weaponSelected=selectedWeaponIndex===i;",
    "const displayActive=weaponSelected&&tagActive;",
    "el.classList.toggle('tag-state-on',Boolean(label)&&displayActive);",
    "el.classList.toggle('tag-state-off',Boolean(label)&&!displayActive);",
]:
    if expected not in final_view:
        raise SystemExit("V31.142 View acceptance failed: " + expected)

for forbidden in [
    ".weapon-tags .weapon-tag.tag-state-off{color:var(--muted)!important}",
    ".weapon-tags .weapon-tag.tag-state-off{background:rgba(154,160,166,.5)",
]:
    if forbidden in final_view:
        raise SystemExit("V31.142 acceptance failed: wrong muted Weapon Tag treatment remains")

for expected in [
    "<title>WH40k 11th V31.142</title>",
    "The current baseline is WH40k_11th_V31.142;",
    'const APP_VERSION = "31.142";',
    "version: 'V31.142',",
    "CHANGE NOTE - WH40k_11th_V31.142",
]:
    if expected not in text:
        raise SystemExit("V31.142 release acceptance failed: " + expected)

path.write_text(text, encoding="utf-8")
print("Built V31.142: muted Weapon Tags now match V31.132 compact muted-box text treatment")
