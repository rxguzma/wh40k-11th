from pathlib import Path
import html
import re

path = Path('WH40k_11th.html')
text = path.read_text(encoding='utf-8')


def once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


# Sequential release metadata.
once('<title>WH40k 11th V31.93</title>', '<title>WH40k 11th V31.94</title>', 'title')
once('The current baseline is WH40k_11th_V31.93;', 'The current baseline is WH40k_11th_V31.94;', 'baseline')
once('const APP_VERSION = "31.93";', 'const APP_VERSION = "31.94";', 'APP_VERSION')
once("version: 'V31.93',", "version: 'V31.94',", 'quality version')

# ---------------------------------------------------------------------------
# Parent/model bridge: attach the exact canonical Old Edit points total to each
# ordered Unit row. getRosterEntryModels() already owns Unit option cost,
# per-model point modifiers, Enhancement points, deletion behavior, etc.
# ---------------------------------------------------------------------------
old_row_return = '    return data ? Object.assign({ kind: "unit" }, data) : null;'
new_row_return = '    return data ? Object.assign({ kind: "unit" }, data, { points: Math.max(0, Number(item.points && item.points.total) || 0) }) : null;'
once(old_row_return, new_row_return, 'ordered roster-row points contract')

# ---------------------------------------------------------------------------
# New View unified EDIT state.
# ---------------------------------------------------------------------------
view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('New View iframe missing')
view_np = html.unescape(vm.group(2))

# Points in column P are a plain Old Edit-style value, not a fourth action.
old_points = r'''  const points=document.createElement('button');
  points.type='button';points.className='unified-edit-action unified-edit-points';points.style.gridColumn='16';points.setAttribute('aria-label','Points');
  const pointValue=data&&(data.points??data.pts??data.totalPoints??data.unitPoints);
  points.textContent=pointValue===undefined||pointValue===null||pointValue===''?'P':String(pointValue);
  r.appendChild(points);'''
new_points = r'''  const points=document.createElement('div');
  points.className='edit-unit-points unified-edit-points';points.style.gridColumn='16';
  const pointValue=Math.max(0,Number(data&&data.points)||0);
  points.textContent=String(pointValue);
  r.appendChild(points);'''
if view_np.count(old_points) != 1:
    raise SystemExit(f'New View Edit points renderer: expected 1 match, found {view_np.count(old_points)}')
view_np = view_np.replace(old_points, new_points, 1)

# Remove the V31.90 one-off small-button Points styling so the value inherits the
# existing .edit-unit-points typography used by the Edit-row visual system.
old_points_css = '.unified-edit-points{font-size:11px}'
if view_np.count(old_points_css) != 1:
    raise SystemExit(f'New View Edit points CSS: expected 1 match, found {view_np.count(old_points_css)}')
view_np = view_np.replace(old_points_css, '', 1)

# Sum the exact point values carried by the visible ordered Unit rows and own the
# EDIT-mode title total from that sheet. Spacer rows contribute zero.
refresh_end_marker = 'window.refreshUnifiedEditRows=refreshUnifiedEditRows;'
if view_np.count(refresh_end_marker) != 1:
    raise SystemExit('New View unified Edit refresh marker missing')
old_refresh_tail = r'''  const mainButton=grid.querySelector('.top-main-button');
  if(mainButton)mainButton.style.gridRow=String(cursor+1);
  return rows.some(row=>row&&row.kind==='unit');
}
window.refreshUnifiedEditRows=refreshUnifiedEditRows;'''
new_refresh_tail = r'''  const mainButton=grid.querySelector('.top-main-button');
  if(mainButton)mainButton.style.gridRow=String(cursor+1);
  const sheetPoints=rows.reduce((sum,row)=>{
    if(!row||row.kind!=='unit')return sum;
    const value=Number(row.points);
    return sum+(Number.isFinite(value)?Math.max(0,value):0);
  },0);
  const titlePoints=grid.querySelector('.top-summary-rest');
  if(titlePoints)titlePoints.textContent='- '+String(sheetPoints)+' pts';
  return rows.some(row=>row&&row.kind==='unit');
}
window.refreshUnifiedEditRows=refreshUnifiedEditRows;
function refreshUnifiedEdit(){
  refreshNewViewTitleFromLegacy();
  return refreshUnifiedEditRows();
}
window.refreshUnifiedEdit=refreshUnifiedEdit;'''
if view_np.count(old_refresh_tail) != 1:
    raise SystemExit(f'New View unified Edit refresh tail: expected 1 match, found {view_np.count(old_refresh_tail)}')
view_np = view_np.replace(old_refresh_tail, new_refresh_tail, 1)

# Run title header first and the sheet-row total second, deterministically, so
# the EDIT title always ends on the sum of this sheet rather than roster-header
# points arriving in a separate animation-frame callback.
old_edit_post = "if(p==='edit'){requestAnimationFrame(refreshNewViewTitleFromLegacy);requestAnimationFrame(refreshUnifiedEditRows)}"
new_edit_post = "if(p==='edit'){requestAnimationFrame(refreshUnifiedEdit)}"
if view_np.count(old_edit_post) != 1:
    raise SystemExit(f'New View unified Edit post-render path: expected 1 match, found {view_np.count(old_edit_post)}')
view_np = view_np.replace(old_edit_post, new_edit_post, 1)

# Write the modified New View document back.
view_srcdoc = html.escape(view_np, quote=True)
text = text[:vm.start(2)] + view_srcdoc + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.94
    Scope: Correct unified New View EDIT points to use the same canonical roster-model totals as Old Edit. getAlternateViewRosterRows now carries each Unit model's points.total, which already includes the selected Unit point option, active per-model point modifiers, and paid Enhancement points. In New View EDIT, column P is now a plain Edit-style numeric point value rather than a Points button/icon or guessed fallback field. The EDIT title point total is recalculated from the ordered Unit rows shown on that sheet, ignoring spacer rows, after the normal legacy title fields refresh. VIEW title behavior, the V31.92 processing lock, and the V31.93 frozen snapshot remain unchanged.
    Risk areas: Parent ordered-row point field plus unified New View EDIT row/title point presentation only. VIEW frozen-snapshot behavior, Old Edit, New Edit, Cards, persistence, CSV data, Waha routing, and Probable remain unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.93\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

# Retain only the five newest V31 detailed notes.
notes = list(re.finditer(r'\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n', text, re.S))
for match in reversed(notes[5:]):
    text = text[:match.start()] + text[match.end():]

# Final acceptance checks.
vm = view_pat.search(text)
if not vm:
    raise SystemExit('New View iframe missing after writeback')
final_view = html.unescape(vm.group(2))

required_view = [
    "points.className='edit-unit-points unified-edit-points'",
    "const pointValue=Math.max(0,Number(data&&data.points)||0);",
    "const sheetPoints=rows.reduce((sum,row)=>{",
    "if(!row||row.kind!=='unit')return sum;",
    "if(titlePoints)titlePoints.textContent='- '+String(sheetPoints)+' pts';",
    'function refreshUnifiedEdit(){',
    'refreshNewViewTitleFromLegacy();',
    'return refreshUnifiedEditRows();',
    "if(p==='edit'){requestAnimationFrame(refreshUnifiedEdit)}",
    'let frozenNewViewSnapshot=null;',
    'function renderFrozenNewView()',
    "function newViewProcessingLocked(){return Boolean(newViewHeaderLocked&&activePageMode==='view')}",
]
for value in required_view:
    if value not in final_view:
        raise SystemExit('V31.94 New View acceptance failed: ' + value)

for forbidden in [
    "points.type='button'",
    "points.setAttribute('aria-label','Points')",
    'data.points??data.pts??data.totalPoints??data.unitPoints',
    "?'P':String(pointValue)",
    '.unified-edit-points{font-size:11px}',
    old_edit_post,
]:
    if forbidden in final_view:
        raise SystemExit('V31.94 retired Edit points behavior remains: ' + forbidden)

required_outer = [
    '<title>WH40k 11th V31.94</title>',
    'const APP_VERSION = "31.94";',
    "version: 'V31.94',",
    'Object.assign({ kind: "unit" }, data, { points: Math.max(0, Number(item.points && item.points.total) || 0) })',
    'CHANGE NOTE - WH40k_11th_V31.94',
]
for value in required_outer:
    if value not in text:
        raise SystemExit('V31.94 acceptance failed: ' + value)

# V31.92/V31.93 lock/snapshot contracts must survive this Edit-only points pass.
if final_view.count('if(newViewProcessingLocked())return false;') < 3:
    raise SystemExit('V31.94 regressed New View processing gates')
if 'frozenNewViewSnapshot=snapshot;activateNewViewSnapshot(snapshot);newViewHeaderLocked=true;' not in final_view:
    raise SystemExit('V31.94 regressed frozen snapshot activation')

path.write_text(text, encoding='utf-8')
print('Built V31.94: unified Edit uses canonical row points and sheet-summed title points')
