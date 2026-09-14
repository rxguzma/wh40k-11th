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
replace_once("<title>WH40k 11th V31.133</title>", "<title>WH40k 11th V31.134</title>", "title")
replace_once(
    "The current baseline is WH40k_11th_V31.133;",
    "The current baseline is WH40k_11th_V31.134;",
    "baseline",
)
replace_once('const APP_VERSION = "31.133";', 'const APP_VERSION = "31.134";', "APP_VERSION")
replace_once("version: 'V31.133',", "version: 'V31.134',", "quality version")

view_pat = re.compile(
    r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)',
    re.S,
)
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing")
view_np = html.unescape(vm.group(2))

# Baseline contracts: use only existing New View elements/states. No new rows,
# dimensions, borders, stat values, or selection behavior are introduced.
for required in [
    ".view-stat-header{",
    ".view-stat-label{",
    ".view-focus-separator{",
    ".weapon-tags.weapon-muted .weapon-tag{color:var(--muted)}",
    "function resetViewStatHeaderFocusPosition(){",
    "function placeViewStatHeaderInFocusRow(row){",
]:
    if required not in view_np:
        raise SystemExit("V31.134 baseline contract missing: " + required)

# Mark only the existing stat header while it is physically sitting in the top
# focus/separator row. Closing/changing focus removes the class and restores the
# normal authored header styling outside the open-Unit state.
old_reset = r'''function resetViewStatHeaderFocusPosition(){
  const header=grid.querySelector('.view-stat-header');
  if(!header)return;
  header.style.removeProperty('grid-row');
  header.style.removeProperty('z-index');
}'''
new_reset = r'''function resetViewStatHeaderFocusPosition(){
  const header=grid.querySelector('.view-stat-header');
  if(!header)return;
  header.classList.remove('view-stat-header-focus');
  header.style.removeProperty('grid-row');
  header.style.removeProperty('z-index');
}'''
if view_np.count(old_reset) != 1:
    raise SystemExit(f"stat header reset hook: expected 1 match, found {view_np.count(old_reset)}")
view_np = view_np.replace(old_reset, new_reset, 1)

old_place = r'''function placeViewStatHeaderInFocusRow(row){
  const header=grid.querySelector('.view-stat-header');
  if(!header||!Number.isFinite(row))return false;
  header.style.gridRow=String(row);
  // The existing focus separator remains the full-width gray background.
  // Raise only the existing stat header above it so M/T/SV/W/LD/OC are visible.
  header.style.zIndex='8';
  return true;
}'''
new_place = r'''function placeViewStatHeaderInFocusRow(row){
  const header=grid.querySelector('.view-stat-header');
  if(!header||!Number.isFinite(row))return false;
  header.classList.add('view-stat-header-focus');
  header.style.gridRow=String(row);
  // The existing focus separator is the full-width gray background.
  // Raise only the existing stat header above it so M/T/SV/W/LD/OC are visible.
  header.style.zIndex='8';
  return true;
}'''
if view_np.count(old_place) != 1:
    raise SystemExit(f"stat header placement hook: expected 1 match, found {view_np.count(old_place)}")
view_np = view_np.replace(old_place, new_place, 1)

# Presentation-only New View overrides. The focused header is transparent so the
# single rgba separator layer remains visually uniform across all 16 columns;
# this avoids double alpha compositing under columns 9-16. Muted Weapon Tag
# interiors use the same gray. Active/selected Tag rules are not touched.
style_end = view_np.find("</style>")
if style_end < 0:
    raise SystemExit("Unified View style block closing tag missing")
if "/* V31.134 New View muted-gray presentation */" in view_np:
    raise SystemExit("V31.134 presentation CSS already present")
css = r'''
/* V31.134 New View muted-gray presentation */
.view-focus-separator{background:rgba(154,160,166,.5)}
.view-stat-header.view-stat-header-focus{background:transparent}
.view-stat-header.view-stat-header-focus .view-stat-label{color:var(--muted);font:700 var(--meta)/1 Roboto,Arial,sans-serif}
.weapon-tags.weapon-muted .weapon-tag{background:rgba(154,160,166,.5)}
'''
view_np = view_np[:style_end] + css + view_np[style_end:]

text = text[: vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2) :]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.134
    Scope: New View presentation only. Use rgba(154,160,166,.5) for the existing top/bottom focus separator rows and for the interior/background of muted Weapon Tag boxes. When a Unit is open, the existing M\", T, SV, W, LD, and OC stat header is marked only while it sits on the top separator row; its own background becomes transparent so the single full-width separator gray remains visually uniform across all 16 columns, and the stat labels use the same muted-Tag font treatment (Roboto 12px bold with muted text color). Active/selected Tag styling is unchanged. Stat values, grid structure, spacing, sizing, borders, row placement, selection logic, filtering, Abilities, Weapons, and all behavior remain unchanged.
    Risk areas: Unified New View muted Weapon Tag background and focused stat-header presentation only. No Edit presentation, data, CSVs, persistence, Probable, lock/FIX, Cards, Waha, or Version behavior changes.
  -->

'''
marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.133\n"
if text.count(marker) != 1:
    raise SystemExit("V31.133 change-note insertion marker missing")
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
    "/* V31.134 New View muted-gray presentation */",
    ".view-focus-separator{background:rgba(154,160,166,.5)}",
    ".view-stat-header.view-stat-header-focus{background:transparent}",
    ".view-stat-header.view-stat-header-focus .view-stat-label{color:var(--muted);font:700 var(--meta)/1 Roboto,Arial,sans-serif}",
    ".weapon-tags.weapon-muted .weapon-tag{background:rgba(154,160,166,.5)}",
    "header.classList.add('view-stat-header-focus');",
    "header.classList.remove('view-stat-header-focus');",
    "header.style.gridRow=String(row);",
    "header.style.zIndex='8';",
]:
    if expected not in final_view:
        raise SystemExit("V31.134 View acceptance failed: " + expected)

# Protect the existing layout/behavior anchors that this presentation patch must
# not replace or remove. Active/selected Tag CSS is intentionally not rewritten.
for required in [
    ".weapon-tags.weapon-muted .weapon-tag{color:var(--muted)}",
    "function applyViewWeaponTagFocus(){",
    "function renderNewViewAbilitiesAndReflow(){",
    "function applyViewFocusSpacing(){",
]:
    if required not in final_view:
        raise SystemExit("V31.134 preserved View contract missing: " + required)

for expected in [
    "<title>WH40k 11th V31.134</title>",
    "The current baseline is WH40k_11th_V31.134;",
    'const APP_VERSION = "31.134";',
    "version: 'V31.134',",
    "CHANGE NOTE - WH40k_11th_V31.134",
]:
    if expected not in text:
        raise SystemExit("V31.134 release acceptance failed: " + expected)

path.write_text(text, encoding="utf-8")
print("Built V31.134: New View muted Tag interiors and focused stat header use separator gray")
