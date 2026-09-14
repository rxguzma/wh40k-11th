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
once("<title>WH40k 11th V31.122</title>", "<title>WH40k 11th V31.123</title>", "title")
once(
    "The current baseline is WH40k_11th_V31.122;",
    "The current baseline is WH40k_11th_V31.123;",
    "baseline",
)
once('const APP_VERSION = "31.122";', 'const APP_VERSION = "31.123";', "APP_VERSION")
once("version: 'V31.122',", "version: 'V31.123',", "quality version")

view_pat = re.compile(
    r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)',
    re.S,
)
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing")
view_np = html.unescape(vm.group(2))

# Preserve the existing V31.120 focus styling and add only the two blank focus
# separator rows. Reuse the existing card gray and grid border variables.
css_anchor = ".view-selected-weapon-wrap{z-index:9}"
separator_css = r'''
.view-focus-separator{grid-column:1/span 16;height:var(--cell);align-self:stretch;justify-self:stretch;background:var(--card);border:1px solid var(--border);border-radius:4px;box-sizing:border-box;pointer-events:none;z-index:7}
'''
if view_np.count(css_anchor) != 1:
    raise SystemExit(f"focus CSS anchor: expected 1 match, found {view_np.count(css_anchor)}")
if ".view-focus-separator{" in view_np:
    raise SystemExit("V31.123 separator CSS already present")
view_np = view_np.replace(css_anchor, css_anchor + separator_css, 1)

# Insert reversible grid-row spacing helpers immediately before the existing
# V31.120 presentation sync. The original layout remains authoritative: before
# every layout/selection refresh we restore original rows, let the existing
# renderer run, then reserve one full row above the active Unit and one below
# its final expanded content row.
helper_anchor = "function syncViewSelectionPresentation(){"
if view_np.count(helper_anchor) != 1:
    raise SystemExit(f"focus helper anchor: expected 1 match, found {view_np.count(helper_anchor)}")

focus_helpers = r'''function viewGridRowNumber(el){
  if(!el)return NaN;
  const inline=String(el.style.gridRow||'').trim();
  const computed=String(getComputedStyle(el).gridRowStart||'').trim();
  const value=parseInt(inline||computed,10);
  return Number.isFinite(value)?value:NaN;
}
function shiftViewFocusGridRow(el,delta){
  if(!el||!delta)return false;
  const row=viewGridRowNumber(el);
  if(!Number.isFinite(row))return false;
  if(!Object.prototype.hasOwnProperty.call(el.dataset,'viewFocusOriginalGridRow')){
    el.dataset.viewFocusOriginalGridRow=el.style.gridRow||'__EMPTY__';
  }
  el.style.gridRow=String(row+delta);
  return true;
}
function clearViewFocusSpacing(){
  grid.querySelectorAll('.view-focus-separator').forEach(el=>el.remove());
  grid.querySelectorAll('[data-view-focus-original-grid-row]').forEach(el=>{
    const original=el.dataset.viewFocusOriginalGridRow;
    if(original==='__EMPTY__')el.style.removeProperty('grid-row');
    else el.style.gridRow=original;
    delete el.dataset.viewFocusOriginalGridRow;
  });
}
function addViewFocusSeparator(row,position){
  if(!Number.isFinite(row))return null;
  const separator=document.createElement('div');
  separator.className='view-focus-separator view-focus-separator-'+position;
  separator.setAttribute('aria-hidden','true');
  separator.style.gridRow=String(row);
  grid.appendChild(separator);
  return separator;
}
function applyViewFocusSpacing(){
  if(activePageMode!=='view'||activeUnitIndex===null)return;
  const activeRow=unitRow(activeUnitIndex);
  if(!activeRow||!viewPresentationVisible(activeRow))return;
  const activeBaseRow=viewGridRowNumber(activeRow);
  if(!Number.isFinite(activeBaseRow))return;

  // Reserve the top separator row. The active Unit moves down one row; every
  // later roster/spacer row moves down two rows to reserve both separators.
  grid.querySelectorAll('.dynamic-roster-row').forEach(el=>{
    const row=viewGridRowNumber(el);
    if(!Number.isFinite(row))return;
    if(el===activeRow)shiftViewFocusGridRow(el,1);
    else if(row>activeBaseRow)shiftViewFocusGridRow(el,2);
  });
  const mainButton=grid.querySelector('.top-main-button');
  if(mainButton&&viewGridRowNumber(mainButton)>activeBaseRow)shiftViewFocusGridRow(mainButton,2);

  // Keep the entire expanded Unit stack together by moving its existing detail,
  // weapon, and tag rows down exactly one row with the Unit.
  const contentNodes=[];
  const seen=new Set();
  const addContentNode=el=>{
    if(!el||seen.has(el)||!viewPresentationVisible(el))return;
    seen.add(el);contentNodes.push(el);
  };
  addContentNode(grid.querySelector('.detail-box-row'));
  addContentNode(grid.querySelector('.weapon-header:not(.boyz-subunit-node)'));
  grid.querySelectorAll('.weapon-row,.weapon-tags,.boyz-subunit-node').forEach(addContentNode);
  contentNodes.forEach(el=>shiftViewFocusGridRow(el,1));

  addViewFocusSeparator(activeBaseRow,'top');
  let bottomRow=viewGridRowNumber(activeRow);
  contentNodes.forEach(el=>{
    const row=viewGridRowNumber(el);
    if(Number.isFinite(row))bottomRow=Math.max(bottomRow,row);
  });
  addViewFocusSeparator(bottomRow+1,'bottom');
  if(typeof syncNewViewFrameHeight==='function')syncNewViewFrameHeight();
}
'''
view_np = view_np.replace(helper_anchor, focus_helpers + "\n" + helper_anchor, 1)

old_sync_wrapper = r'''syncWeaponLayout=function(){
  const result=syncWeaponLayoutV31119.apply(this,arguments);
  syncViewSelectionPresentation();
  return result;
};'''
new_sync_wrapper = r'''syncWeaponLayout=function(){
  const focusLocked=typeof newViewHeaderLocked!=='undefined'&&newViewHeaderLocked;
  if(!focusLocked)clearViewFocusSpacing();
  const result=syncWeaponLayoutV31119.apply(this,arguments);
  if(!focusLocked)applyViewFocusSpacing();
  syncViewSelectionPresentation();
  return result;
};'''
if view_np.count(old_sync_wrapper) != 1:
    raise SystemExit(f"syncWeaponLayout focus wrapper: expected 1 match, found {view_np.count(old_sync_wrapper)}")
view_np = view_np.replace(old_sync_wrapper, new_sync_wrapper, 1)

old_boyz_wrapper = r'''refreshBoyzNewViewSelection=function(){
  const result=refreshBoyzNewViewSelectionV31119.apply(this,arguments);
  syncViewSelectionPresentation();
  return result;
};'''
new_boyz_wrapper = r'''refreshBoyzNewViewSelection=function(){
  const focusLocked=typeof newViewHeaderLocked!=='undefined'&&newViewHeaderLocked;
  if(!focusLocked)clearViewFocusSpacing();
  const result=refreshBoyzNewViewSelectionV31119.apply(this,arguments);
  if(!focusLocked)applyViewFocusSpacing();
  syncViewSelectionPresentation();
  return result;
};'''
if view_np.count(old_boyz_wrapper) != 1:
    raise SystemExit(f"Boyz focus wrapper: expected 1 match, found {view_np.count(old_boyz_wrapper)}")
view_np = view_np.replace(old_boyz_wrapper, new_boyz_wrapper, 1)

# Keep resize behavior aligned with the new physical separator rows before the
# existing wrap boxes are recalculated.
old_resize = "window.addEventListener('resize',()=>{if(activePageMode==='view'&&!newViewHeaderLocked)syncViewSelectionPresentation()});"
new_resize = "window.addEventListener('resize',()=>{if(activePageMode==='view'&&!newViewHeaderLocked){clearViewFocusSpacing();applyViewFocusSpacing();syncViewSelectionPresentation()}});"
if view_np.count(old_resize) != 1:
    raise SystemExit(f"focus resize handler: expected 1 match, found {view_np.count(old_resize)}")
view_np = view_np.replace(old_resize, new_resize, 1)

text = text[: vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2) :]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.123
    Scope: Add two full-width blank gray focus rows around the currently opened Unit in unified View. One existing-card-gray row appears immediately above the active Unit and one immediately below the final visible Unit detail/weapon/tag row. The active Unit plus its expanded content remains inside the existing Unit wrap box between those separators; the selected-Weapon wrap remains unchanged. Separator rows disappear when the Unit closes or focus changes. No text or controls are added to the separators.
    Risk areas: Unified View expanded-Unit grid-row spacing only. Existing muted/active colors, Unit and selected-Weapon wrap boxes, roster/weapon data, filters, Boyz selection, lock/frozen behavior, scrolling/frame sizing, Edit, FIX, Cards, persistence, CSV data, Waha routing, Probable, and Version controls remain unchanged.
  -->

'''
marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.122\n"
if text.count(marker) != 1:
    raise SystemExit("V31.122 change-note insertion marker missing")
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

# Acceptance checks.
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing after writeback")
final_view = html.unescape(vm.group(2))

for expected in [
    ".view-focus-separator{grid-column:1/span 16;height:var(--cell);",
    "background:var(--card);border:1px solid var(--border);",
    "function clearViewFocusSpacing(){",
    "function applyViewFocusSpacing(){",
    "grid.querySelectorAll('.dynamic-roster-row').forEach(el=>{",
    "if(el===activeRow)shiftViewFocusGridRow(el,1);",
    "else if(row>activeBaseRow)shiftViewFocusGridRow(el,2);",
    "contentNodes.forEach(el=>shiftViewFocusGridRow(el,1));",
    "addViewFocusSeparator(activeBaseRow,'top');",
    "addViewFocusSeparator(bottomRow+1,'bottom');",
    "if(!focusLocked)clearViewFocusSpacing();",
    "if(!focusLocked)applyViewFocusSpacing();",
    "function syncViewSelectionPresentation(){",
    "addViewSelectionWrap('view-open-unit-wrap',activeRow,unitParts);",
    "addViewSelectionWrap('view-selected-weapon-wrap',selected.row,selectedParts);",
]:
    if expected not in final_view:
        raise SystemExit("V31.123 View acceptance failed: " + expected)

for expected in [
    "<title>WH40k 11th V31.123</title>",
    "The current baseline is WH40k_11th_V31.123;",
    'const APP_VERSION = "31.123";',
    "version: 'V31.123',",
    "CHANGE NOTE - WH40k_11th_V31.123",
]:
    if expected not in text:
        raise SystemExit("V31.123 release acceptance failed: " + expected)

path.write_text(text, encoding="utf-8")
print("Built V31.123: gray focus separator rows above and below the opened Unit")
