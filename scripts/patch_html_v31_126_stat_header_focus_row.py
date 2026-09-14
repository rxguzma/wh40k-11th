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
once("<title>WH40k 11th V31.125</title>", "<title>WH40k 11th V31.126</title>", "title")
once(
    "The current baseline is WH40k_11th_V31.125;",
    "The current baseline is WH40k_11th_V31.126;",
    "baseline",
)
once('const APP_VERSION = "31.125";', 'const APP_VERSION = "31.126";', "APP_VERSION")
once("version: 'V31.125',", "version: 'V31.126',", "quality version")

view_pat = re.compile(
    r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)',
    re.S,
)
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing")
view_np = html.unescape(vm.group(2))

# This change reuses the existing stat-header DOM. When a Unit is focused, the
# existing header is visually moved onto the already-existing top focus row.
# No duplicate stat labels/header are created and no stat header is deleted.
for required in [
    ".view-stat-header{",
    "function clearViewFocusSpacing(){",
    "function applyViewFocusSpacing(){",
    "addViewFocusSeparator(activeBaseRow,'top');",
    ".view-focus-separator{",
]:
    if required not in view_np:
        raise SystemExit("V31.126 baseline contract missing: " + required)

helper_anchor = "function clearViewFocusSpacing(){"
if view_np.count(helper_anchor) != 1:
    raise SystemExit(
        f"stat-header helper anchor: expected 1 match, found {view_np.count(helper_anchor)}"
    )

helpers = r'''function resetViewStatHeaderFocusPosition(){
  const header=grid.querySelector('.view-stat-header');
  if(!header)return;
  header.style.removeProperty('grid-row');
  header.style.removeProperty('z-index');
}
function placeViewStatHeaderInFocusRow(row){
  const header=grid.querySelector('.view-stat-header');
  if(!header||!Number.isFinite(row))return false;
  header.style.gridRow=String(row);
  // The existing focus separator remains the full-width gray background.
  // Raise only the existing stat header above it so M/T/SV/W/LD/OC are visible.
  header.style.zIndex='8';
  return true;
}
'''
view_np = view_np.replace(helper_anchor, helpers + "\n" + helper_anchor, 1)

old_clear = r'''function clearViewFocusSpacing(){
  grid.querySelectorAll('.view-focus-separator').forEach(el=>el.remove());'''
new_clear = r'''function clearViewFocusSpacing(){
  resetViewStatHeaderFocusPosition();
  grid.querySelectorAll('.view-focus-separator').forEach(el=>el.remove());'''
if view_np.count(old_clear) != 1:
    raise SystemExit(
        f"focus clear hook: expected 1 match, found {view_np.count(old_clear)}"
    )
view_np = view_np.replace(old_clear, new_clear, 1)

old_top = "  addViewFocusSeparator(activeBaseRow,'top');"
new_top = "  addViewFocusSeparator(activeBaseRow,'top');\n  placeViewStatHeaderInFocusRow(activeBaseRow);"
if view_np.count(old_top) != 1:
    raise SystemExit(
        f"top focus-row hook: expected 1 match, found {view_np.count(old_top)}"
    )
view_np = view_np.replace(old_top, new_top, 1)

text = text[: vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2) :]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.126
    Scope: In unified New View, when a Unit opens, reuse the existing M/T/SV/W/LD/OC stat-header element in the existing blank gray focus row immediately above that Unit. The header no longer remains visible in its old fixed row while a Unit is open because the same DOM element is visually repositioned to the top focus row. Closing the Unit restores the header to its normal authored position. No duplicate stat header or labels are created, and no stat header or stat-label elements are deleted. Existing grid dimensions, fonts, colors, stat columns, Unit row, focus separator, Unit data, and expanded content remain unchanged.
    Risk areas: Unified New View stat-header grid-row presentation while a Unit is focused only. No roster/CSV data, Unit/Weapon/Ability rendering, Edit, lock prepared-state behavior, report storage, Waha, Cards, Probable, persistence, or Version controls change.
  -->

'''
marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.125\n"
if text.count(marker) != 1:
    raise SystemExit("V31.125 change-note insertion marker missing")
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
    "function resetViewStatHeaderFocusPosition(){",
    "function placeViewStatHeaderInFocusRow(row){",
    "const header=grid.querySelector('.view-stat-header');",
    "header.style.removeProperty('grid-row');",
    "header.style.gridRow=String(row);",
    "header.style.zIndex='8';",
    "resetViewStatHeaderFocusPosition();",
    "addViewFocusSeparator(activeBaseRow,'top');\n  placeViewStatHeaderInFocusRow(activeBaseRow);",
]:
    if expected not in final_view:
        raise SystemExit("V31.126 View acceptance failed: " + expected)

# Do not introduce a second stat-header builder or any removal of the existing
# stat header/labels as part of this change.
if final_view.count("function addViewStatHeader(f)") != 1:
    raise SystemExit("V31.126 stat-header builder count changed")
for forbidden in [
    "grid.querySelector('.view-stat-header').remove()",
    'grid.querySelectorAll(\'.view-stat-label\').forEach(el=>el.remove())',
]:
    if forbidden in final_view:
        raise SystemExit("V31.126 attempted stat-header deletion: " + forbidden)

for expected in [
    "<title>WH40k 11th V31.126</title>",
    "The current baseline is WH40k_11th_V31.126;",
    'const APP_VERSION = "31.126";',
    "version: 'V31.126',",
    "CHANGE NOTE - WH40k_11th_V31.126",
]:
    if expected not in text:
        raise SystemExit("V31.126 release acceptance failed: " + expected)

path.write_text(text, encoding="utf-8")
print("Built V31.126: existing stat header moves into the top focus row for an open Unit")
