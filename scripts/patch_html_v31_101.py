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
once('<title>WH40k 11th V31.100</title>', '<title>WH40k 11th V31.101</title>', 'title')
once('The current baseline is WH40k_11th_V31.100;', 'The current baseline is WH40k_11th_V31.101;', 'baseline')
once('const APP_VERSION = "31.100";', 'const APP_VERSION = "31.101";', 'APP_VERSION')
once("version: 'V31.100',", "version: 'V31.101',", 'quality version')

# Carry the canonical roster-model point-option state into each ordered row.
# This is the same model used by Old Edit/Boyz: one roster entry, one selected
# option, and no duplicate Unit rows.
old_row_return = '    return data ? Object.assign({ kind: "unit" }, data, { points: Math.max(0, Number(item.points && item.points.total) || 0) }) : null;'
new_row_return = '    return data ? Object.assign({ kind: "unit" }, data, { entryId: String(item.entryId || ""), points: Math.max(0, Number(item.points && item.points.total) || 0), pointLabel: String(item.points && item.points.label || ""), pointToggleEnabled: Boolean(item.points && item.points.toggleEnabled) }) : null;'
once(old_row_return, new_row_return, 'ordered roster-row point-option contract')

# The legacy roster action is the source-of-truth mutation used by Boyz and
# every other selectable point-option Unit. Do not duplicate that logic here.
if 'toggleViewEditRosterEntryPointOption' not in text:
    raise SystemExit('Legacy point-option toggle is missing')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('New View iframe missing')
view_np = html.unescape(vm.group(2))

# Copy the established Boyz point-label visual language into the isolated New
# View iframe. The iframe cannot inherit Old Edit CSS from the parent document.
style_marker = '</style>'
if view_np.count(style_marker) < 1:
    raise SystemExit('New View style close marker missing')
point_css = '''
.point-option-toggle{display:inline-block;margin-left:8px;padding:2px 7px;border-radius:999px;border:1px solid #48515f;background:#2b313b;color:#80d6a3;font:900 var(--meta)/1.2 Roboto,Arial,sans-serif;cursor:pointer;user-select:none;-webkit-user-select:none;vertical-align:1px;white-space:nowrap;appearance:none;-webkit-appearance:none}
.point-option-toggle:active{background:#3a4350;transform:translateY(1px)}
.point-option-label-static{display:inline-block;margin-left:8px;color:#80d6a3;font:900 var(--meta)/1.2 Roboto,Arial,sans-serif;vertical-align:1px;white-space:nowrap}
'''
view_np = view_np.replace(style_marker, point_css + style_marker, 1)

# In unified Edit, append the selected x-label to the Unit name. A selectable
# label delegates the click to the existing parent roster action, then re-reads
# the canonical rows so label, column-P points, and the sheet total all update.
old_name = r'''  const n=document.createElement('div');
  n.className='edit-unit-name';
  n.textContent=String(data&&data.name||'');
  r.appendChild(n);'''
new_name = r'''  const n=document.createElement('div');
  n.className='edit-unit-name';
  const nameText=document.createElement('span');
  nameText.textContent=String(data&&data.name||'');
  n.appendChild(nameText);
  const pointLabel=String(data&&data.pointLabel||'').trim();
  if(pointLabel){
    const canToggle=Boolean(data&&data.pointToggleEnabled&&data.entryId);
    const label=document.createElement(canToggle?'button':'span');
    if(canToggle)label.type='button';
    label.className=canToggle?'point-option-toggle':'point-option-label-static';
    label.textContent=pointLabel;
    if(canToggle){
      label.setAttribute('aria-label','Change point option');
      label.onclick=(event)=>{
        event.stopPropagation();
        try{
          if(parent&&typeof parent.toggleViewEditRosterEntryPointOption==='function'){
            parent.toggleViewEditRosterEntryPointOption(String(data.entryId||''));
          }
        }catch(_){}
        requestAnimationFrame(refreshUnifiedEdit);
      };
    }
    n.appendChild(label);
  }
  r.appendChild(n);'''
if view_np.count(old_name) != 1:
    raise SystemExit(f'Unified Edit Unit name renderer: expected 1 match, found {view_np.count(old_name)}')
view_np = view_np.replace(old_name, new_name, 1)

# Write the modified New View document back.
text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.101
    Scope: Bring the established Boyz-style selectable point option into unified New View EDIT without duplicating roster logic. Ordered Unit rows now carry the canonical roster entryId, selected point label, toggle-enabled state, and total points from getRosterEntryModels. EDIT renders the selected x-label beside the Unit name using the existing Boyz pill format. Tapping a selectable label delegates to the existing toggleViewEditRosterEntryPointOption action, then refreshes the unified Edit rows from the parent model so the label, column-P points, and Edit title total update together. Units with a non-clickable label show the same green static label. This is generic for all selectable point-option Units and does not hardcode Boyz or create duplicate Unit rows.
    Risk areas: Unified New View EDIT Unit-name point-label presentation and its existing roster point-option action bridge only. VIEW, persistent grid/cache behavior, lock/frozen snapshot, Move/Copy/Dead controls, Old Edit, Cards, CSV data, Weapons, Waha routing, Version controls, and Probable remain unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.100\n'
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
    "const pointLabel=String(data&&data.pointLabel||'').trim();",
    "const canToggle=Boolean(data&&data.pointToggleEnabled&&data.entryId);",
    "label.className=canToggle?'point-option-toggle':'point-option-label-static';",
    "typeof parent.toggleViewEditRosterEntryPointOption==='function'",
    "parent.toggleViewEditRosterEntryPointOption(String(data.entryId||''));",
    'requestAnimationFrame(refreshUnifiedEdit);',
    '.point-option-toggle{display:inline-block;margin-left:8px;padding:2px 7px;',
    '.point-option-label-static{display:inline-block;margin-left:8px;',
    'function renderUnifiedEditRows(rows)',
    'function renderCachedEdit()',
]
for value in required_view:
    if value not in final_view:
        raise SystemExit('V31.101 unified Edit acceptance failed: ' + value)

required_outer = [
    '<title>WH40k 11th V31.101</title>',
    'The current baseline is WH40k_11th_V31.101;',
    'const APP_VERSION = "31.101";',
    "version: 'V31.101',",
    'entryId: String(item.entryId || "")',
    'pointLabel: String(item.points && item.points.label || "")',
    'pointToggleEnabled: Boolean(item.points && item.points.toggleEnabled)',
    'toggleViewEditRosterEntryPointOption',
    'CHANGE NOTE - WH40k_11th_V31.101',
]
for value in required_outer:
    if value not in text:
        raise SystemExit('V31.101 acceptance failed: ' + value)

# Protect the current unified-page and fast-toggle contracts.
for forbidden in ['id="newEditPageScreen"', 'id="npEditFrame"', 'parent.getNewEdit']:
    if forbidden in text:
        raise SystemExit('V31.101 regressed retired standalone New Edit: ' + forbidden)
if 'function ensurePersistentGridCells()' not in final_view or 'function clearModeContent()' not in final_view:
    raise SystemExit('V31.101 regressed V31.100 persistent-grid fast path')

path.write_text(text, encoding='utf-8')
print('Built V31.101: Boyz-style point-option labels in unified Edit')
