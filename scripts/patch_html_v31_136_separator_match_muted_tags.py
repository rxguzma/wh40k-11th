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
replace_once("<title>WH40k 11th V31.135</title>", "<title>WH40k 11th V31.136</title>", "title")
replace_once(
    "The current baseline is WH40k_11th_V31.135;",
    "The current baseline is WH40k_11th_V31.136;",
    "baseline",
)
replace_once('const APP_VERSION = "31.135";', 'const APP_VERSION = "31.136";', "APP_VERSION")
replace_once("version: 'V31.135',", "version: 'V31.136',", "quality version")

view_pat = re.compile(
    r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)',
    re.S,
)
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing")
view_np = html.unescape(vm.group(2))

for required in [
    "/* V31.134 New View muted-gray presentation */",
    ".weapon-tag{",
    "background:var(--btn);",
    ".weapon-tags.weapon-muted .weapon-tag{color:var(--muted)}",
    "function resetViewStatHeaderFocusPosition(){",
    "function placeViewStatHeaderInFocusRow(row){",
]:
    if required not in view_np:
        raise SystemExit("V31.136 baseline contract missing: " + required)

# Correct the V31.134 direction: muted Weapon Tags remain completely untouched
# and authoritative. The two existing focus separator rows now copy the muted
# Tag color treatment instead: shared button background plus muted label text.
# Geometry, sizing, borders, state behavior, and Tag CSS remain unchanged.
old_css = r'''/* V31.134 New View muted-gray presentation */
.view-focus-separator{background:rgba(154,160,166,.5)}
.view-stat-header.view-stat-header-focus{background:transparent}
.view-stat-header.view-stat-header-focus .view-stat-label{color:var(--muted);font:700 var(--meta)/1 Roboto,Arial,sans-serif}
.weapon-tags.weapon-muted .weapon-tag{background:rgba(154,160,166,.5)}'''
new_css = r'''/* V31.136 New View focus rows follow existing muted Weapon Tags */
.view-focus-separator{background:var(--btn)}
.view-stat-header.view-stat-header-focus{background:transparent}
.view-stat-header.view-stat-header-focus .view-stat-label{color:var(--muted);font:700 var(--meta)/1 Roboto,Arial,sans-serif}'''
if view_np.count(old_css) != 1:
    raise SystemExit(f"V31.134 muted-gray override block: expected 1 match, found {view_np.count(old_css)}")
view_np = view_np.replace(old_css, new_css, 1)

text = text[: vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2) :]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.136
    Scope: Correct unified New View muted-color direction. Weapon Tags are restored to their existing authored styling and are no longer recolored by the V31.134 override. The existing top and bottom open-Unit focus separator rows now follow the muted Weapon Tag palette by using the shared Tag/button background var(--btn). The existing M\", T, SV, W, LD, and OC labels on the top row continue to use the muted Tag text/font treatment. Active/selected Tag styling is unchanged. Stat values, grid structure, spacing, sizing, borders, row placement, selection behavior, Weapons, Abilities, and all other behavior remain unchanged.
    Risk areas: Unified New View focus-row color presentation only. No Tag styling/state behavior, Edit presentation, data, CSVs, persistence, Probable, lock/FIX, Cards, Waha, or Version behavior changes.
  -->

'''
marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.135\n"
if text.count(marker) != 1:
    raise SystemExit("V31.135 change-note insertion marker missing")
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
    "/* V31.136 New View focus rows follow existing muted Weapon Tags */",
    ".view-focus-separator{background:var(--btn)}",
    ".view-stat-header.view-stat-header-focus{background:transparent}",
    ".view-stat-header.view-stat-header-focus .view-stat-label{color:var(--muted);font:700 var(--meta)/1 Roboto,Arial,sans-serif}",
    ".weapon-tags.weapon-muted .weapon-tag{color:var(--muted)}",
    "function applyViewWeaponTagFocus(){",
    "function renderNewViewAbilitiesAndReflow(){",
    "function applyViewFocusSpacing(){",
]:
    if expected not in final_view:
        raise SystemExit("V31.136 View acceptance failed: " + expected)

# The mistaken V31.134 Tag recolor must be gone; no replacement Tag-background
# override is permitted in this patch.
for forbidden in [
    ".weapon-tags.weapon-muted .weapon-tag{background:rgba(154,160,166,.5)}",
    ".weapon-tags.weapon-muted .weapon-tag{background:var(--btn)}",
    ".view-focus-separator{background:rgba(154,160,166,.5)}",
]:
    if forbidden in final_view:
        raise SystemExit("V31.136 retained/reintroduced incorrect styling: " + forbidden)

for expected in [
    "<title>WH40k 11th V31.136</title>",
    "The current baseline is WH40k_11th_V31.136;",
    'const APP_VERSION = "31.136";',
    "version: 'V31.136',",
    "CHANGE NOTE - WH40k_11th_V31.136",
]:
    if expected not in text:
        raise SystemExit("V31.136 release acceptance failed: " + expected)

path.write_text(text, encoding="utf-8")
print("Built V31.136: focus rows now follow existing muted Weapon Tag colors; Tags unchanged")
