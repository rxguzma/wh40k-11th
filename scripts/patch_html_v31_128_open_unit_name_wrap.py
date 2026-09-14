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
replace_once("<title>WH40k 11th V31.127</title>", "<title>WH40k 11th V31.128</title>", "title")
replace_once(
    "The current baseline is WH40k_11th_V31.127;",
    "The current baseline is WH40k_11th_V31.128;",
    "baseline",
)
replace_once('const APP_VERSION = "31.127";', 'const APP_VERSION = "31.128";', "APP_VERSION")
replace_once("version: 'V31.127',", "version: 'V31.128',", "quality version")

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


# Closed Unit rows keep the established one-row clipped presentation. Only the
# currently opened Unit receives this class, and only when its name actually
# overflows the existing Unit-name columns.
css_anchor = ".view-unit-row.unit-active .view-unit-name{text-transform:uppercase}"
expanded_css = r'''
.view-unit-row.view-unit-name-expanded{height:auto;min-height:var(--cell);align-self:stretch}
.view-unit-row.view-unit-name-expanded .view-unit-name{height:auto;min-height:var(--cell);align-self:stretch;white-space:normal;overflow:visible;overflow-wrap:anywhere;line-height:1.1;padding-top:4px;padding-bottom:4px}
'''
if view_np.count(css_anchor) != 1:
    raise SystemExit(f"open Unit-name CSS anchor: expected 1 match, found {view_np.count(css_anchor)}")
if ".view-unit-row.view-unit-name-expanded{" in view_np:
    raise SystemExit("V31.128 open Unit-name CSS already present")
view_np = view_np.replace(css_anchor, css_anchor + expanded_css, 1)

# Measure the existing name cell at its authored width. If nowrap is clipping,
# temporarily allow wrapping only for measurement and return the exact number of
# standard grid rows needed. Nothing is widened and short names remain one row.
helper_anchor = "function clearViewFocusSpacing(){"
name_helpers = r'''function viewOpenUnitNameRowSpan(activeRow){
  if(!activeRow)return 1;
  const name=activeRow.querySelector('.view-unit-name');
  if(!name)return 1;
  const available=Math.max(0,name.clientWidth||0);
  if(!available||name.scrollWidth<=available+1)return 1;
  const saved={
    whiteSpace:name.style.whiteSpace,
    height:name.style.height,
    overflow:name.style.overflow,
    overflowWrap:name.style.overflowWrap,
    lineHeight:name.style.lineHeight,
    paddingTop:name.style.paddingTop,
    paddingBottom:name.style.paddingBottom
  };
  name.style.whiteSpace='normal';
  name.style.height='auto';
  name.style.overflow='visible';
  name.style.overflowWrap='anywhere';
  name.style.lineHeight='1.1';
  name.style.paddingTop='4px';
  name.style.paddingBottom='4px';
  const cellPx=parseFloat(getComputedStyle(grid).getPropertyValue('--cell'))||26;
  const needed=Math.max(cellPx,name.scrollHeight||cellPx);
  Object.keys(saved).forEach(key=>{name.style[key]=saved[key]});
  return Math.max(1,Math.ceil(needed/cellPx));
}
'''
if view_np.count(helper_anchor) != 1:
    raise SystemExit(f"open Unit-name helper anchor: expected 1 match, found {view_np.count(helper_anchor)}")
view_np = view_np.replace(helper_anchor, name_helpers + "\n" + helper_anchor, 1)

# Clearing focus must also remove the presentation-only expansion class. The
# existing data-view-focus-original-grid-row restoration remains authoritative
# for returning the Unit to its original single-row placement.
old_clear = r'''function clearViewFocusSpacing(){
  resetViewStatHeaderFocusPosition();
  grid.querySelectorAll('.view-focus-separator').forEach(el=>el.remove());'''
new_clear = r'''function clearViewFocusSpacing(){
  resetViewStatHeaderFocusPosition();
  grid.querySelectorAll('.view-unit-row.view-unit-name-expanded').forEach(el=>el.classList.remove('view-unit-name-expanded'));
  grid.querySelectorAll('.view-focus-separator').forEach(el=>el.remove());'''
view_replace_once(old_clear, new_clear, "open Unit-name focus clear")

# Compute the required span before focus rows move anything. The active Unit is
# still moved down by the existing top separator. When a long name needs extra
# rows, preserve the original row in the existing focus dataset, then apply the
# larger span and shift all expanded content / later roster rows by the same
# extra amount. This keeps the full Unit stack contiguous and non-overlapping.
old_base = r'''  const activeBaseRow=viewGridRowNumber(activeRow);
  if(!Number.isFinite(activeBaseRow))return;

  // Reserve the top separator row.'''
new_base = r'''  const activeBaseRow=viewGridRowNumber(activeRow);
  if(!Number.isFinite(activeBaseRow))return;
  const activeNameRowSpan=viewOpenUnitNameRowSpan(activeRow);
  const activeNameExtraRows=Math.max(0,activeNameRowSpan-1);

  // Reserve the top separator row.'''
view_replace_once(old_base, new_base, "open Unit-name row-span calculation")

old_dynamic = r'''    if(el===activeRow)shiftViewFocusGridRow(el,1);
    else if(row>activeBaseRow)shiftViewFocusGridRow(el,2);'''
new_dynamic = r'''    if(el===activeRow){
      shiftViewFocusGridRow(el,1);
      if(activeNameExtraRows>0){
        const shiftedRow=viewGridRowNumber(el);
        if(Number.isFinite(shiftedRow)){
          el.classList.add('view-unit-name-expanded');
          el.style.gridRow=String(shiftedRow)+' / span '+String(activeNameRowSpan);
        }
      }
    }else if(row>activeBaseRow)shiftViewFocusGridRow(el,2+activeNameExtraRows);'''
view_replace_once(old_dynamic, new_dynamic, "open Unit-name roster shifting")

old_main = "  if(mainButton&&viewGridRowNumber(mainButton)>activeBaseRow)shiftViewFocusGridRow(mainButton,2);"
new_main = "  if(mainButton&&viewGridRowNumber(mainButton)>activeBaseRow)shiftViewFocusGridRow(mainButton,2+activeNameExtraRows);"
view_replace_once(old_main, new_main, "open Unit-name main-button shifting")

old_content = "  contentNodes.forEach(el=>shiftViewFocusGridRow(el,1));"
new_content = "  contentNodes.forEach(el=>shiftViewFocusGridRow(el,1+activeNameExtraRows));"
view_replace_once(old_content, new_content, "open Unit-name detail shifting")

old_bottom = "  let bottomRow=viewGridRowNumber(activeRow);"
new_bottom = "  let bottomRow=viewGridRowNumber(activeRow)+activeNameExtraRows;"
view_replace_once(old_bottom, new_bottom, "open Unit-name bottom bound")

text = text[: vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2) :]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.128
    Scope: Fix long Unit names in unified New View without changing the 16-column grid. Closed Unit rows retain the existing compact single-row/clipped presentation. When a Unit is opened, its existing Unit-name cell is measured at the authored width; only if the name is clipped does that active Unit row wrap and expand vertically by the minimum number of standard grid rows required. Existing detail, Weapon, Ability, later roster, focus separator, and bottom-bound rows shift by the same extra amount so nothing overlaps. Closing or changing focus restores the original single-row Unit geometry.
    Risk areas: Unified New View opened-Unit name presentation and focus-row spacing only. No column widths, fonts, colors, Unit data, stats, Weapons, Abilities, Old Edit, CSV data, lock behavior, report storage, Cards, Waha, Probable, persistence, or Version-control behavior changes.
  -->

'''
marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.127\n"
if text.count(marker) != 1:
    raise SystemExit("V31.127 change-note insertion marker missing")
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
    ".view-unit-row.view-unit-name-expanded{height:auto;min-height:var(--cell);align-self:stretch}",
    "white-space:normal;overflow:visible;overflow-wrap:anywhere;line-height:1.1;",
    "function viewOpenUnitNameRowSpan(activeRow){",
    "if(!available||name.scrollWidth<=available+1)return 1;",
    "const activeNameRowSpan=viewOpenUnitNameRowSpan(activeRow);",
    "const activeNameExtraRows=Math.max(0,activeNameRowSpan-1);",
    "el.classList.add('view-unit-name-expanded');",
    "el.style.gridRow=String(shiftedRow)+' / span '+String(activeNameRowSpan);",
    "shiftViewFocusGridRow(el,2+activeNameExtraRows);",
    "shiftViewFocusGridRow(el,1+activeNameExtraRows)",
    "let bottomRow=viewGridRowNumber(activeRow)+activeNameExtraRows;",
    "placeViewStatHeaderInFocusRow(activeBaseRow);",
]:
    if expected not in final_view:
        raise SystemExit("V31.128 View acceptance failed: " + expected)

# Collapsed rows must retain the original clipping rules; do not globally wrap
# every Unit name or widen the Unit-name grid columns.
for required in [
    "white-space:nowrap",
    "overflow:hidden",
]:
    if required not in final_view:
        raise SystemExit("V31.128 collapsed Unit-name contract missing: " + required)
if ".view-unit-name{grid-column:" not in final_view:
    raise SystemExit("V31.128 Unit-name grid-column contract missing")

for expected in [
    "<title>WH40k 11th V31.128</title>",
    "The current baseline is WH40k_11th_V31.128;",
    'const APP_VERSION = "31.128";',
    "version: 'V31.128',",
    "CHANGE NOTE - WH40k_11th_V31.128",
]:
    if expected not in text:
        raise SystemExit("V31.128 release acceptance failed: " + expected)

path.write_text(text, encoding="utf-8")
print("Built V31.128: long opened Unit names wrap and expand only when needed")
