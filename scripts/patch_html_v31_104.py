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
once('<title>WH40k 11th V31.103</title>', '<title>WH40k 11th V31.104</title>', 'title')
once('The current baseline is WH40k_11th_V31.103;', 'The current baseline is WH40k_11th_V31.104;', 'baseline')
once('const APP_VERSION = "31.103";', 'const APP_VERSION = "31.104";', 'APP_VERSION')
once("version: 'V31.103',", "version: 'V31.104',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing')
view_np = html.unescape(vm.group(2))

# The local mode button currently labels the destination mode, which makes the
# visible VIEW/EDIT state read backwards. Keep the same fast local toggle, but
# label and highlight the mode that is actually active.
old_mode_class = "toggle.className='button-standard';"
new_mode_class = "toggle.className='button-standard active-green';"
if view_np.count(old_mode_class) != 1:
    raise SystemExit(f'mode button class: expected 1 match, found {view_np.count(old_mode_class)}')
view_np = view_np.replace(old_mode_class, new_mode_class, 1)

old_mode_label = "toggle.textContent=p==='view'?'EDIT':'VIEW';"
new_mode_label = "toggle.textContent=p==='view'?'VIEW':'EDIT';"
if view_np.count(old_mode_label) != 1:
    raise SystemExit(f'mode button label: expected 1 match, found {view_np.count(old_mode_label)}')
view_np = view_np.replace(old_mode_label, new_mode_label, 1)

# Standardize the grid control in both local modes. VIEW already uses the
# four-cell grid-mode icon; EDIT still renders the legacy letter G. Reuse the
# exact same icon and styling while preserving the existing mode-specific grid
# position (VIEW stays at P4 because the weapon filter occupies M4:O4).
old_grid_css = ".view-grid-toggle svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round}"
new_grid_css = ".grid-toggle svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round}"
if view_np.count(old_grid_css) != 1:
    raise SystemExit(f'grid icon css: expected 1 match, found {view_np.count(old_grid_css)}')
view_np = view_np.replace(old_grid_css, new_grid_css, 1)

grid_svg = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><rect x="4" y="4" width="6" height="6" rx="1"></rect><rect x="14" y="4" width="6" height="6" rx="1"></rect><rect x="4" y="14" width="6" height="6" rx="1"></rect><rect x="14" y="14" width="6" height="6" rx="1"></rect></svg>'
old_grid_render = "if(p==='view'){gb.innerHTML='" + grid_svg + "'}else{gb.textContent='G'}"
new_grid_render = "gb.innerHTML='" + grid_svg + "'"
if view_np.count(old_grid_render) != 1:
    raise SystemExit(f'grid icon renderer: expected 1 match, found {view_np.count(old_grid_render)}')
view_np = view_np.replace(old_grid_render, new_grid_render, 1)

# The grid-on class already persists across local View/Edit switches. Make the
# newly-rendered button reflect that existing state immediately, instead of
# resetting its visual/ARIA state until the next tap.
old_grid_state = "gb.setAttribute('aria-pressed','false');gb.onclick=()=>{const on=!grid.classList.contains('grid-on');"
new_grid_state = "const gridOn=grid.classList.contains('grid-on');gb.classList.toggle('active-green',gridOn);gb.setAttribute('aria-pressed',gridOn?'true':'false');gb.onclick=()=>{const on=!grid.classList.contains('grid-on');"
if view_np.count(old_grid_state) != 1:
    raise SystemExit(f'grid state sync: expected 1 match, found {view_np.count(old_grid_state)}')
view_np = view_np.replace(old_grid_state, new_grid_state, 1)

# Write unified iframe back.
text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.104
    Scope: Correct the unified New View/Edit mode controls. The single local mode button now displays the mode that is actually active and is highlighted green: VIEW in View mode and EDIT in Edit mode; tapping it still switches directly to the opposite local mode through the existing fast path. The grid control is also standardized across both modes: Edit no longer renders the legacy G and now uses the same four-cell Grid Mode icon, SVG styling, toggle behavior, and current on/off indication as View. Existing mode-specific placement is retained so View's filter layout is unchanged.
    Risk areas: Unified New View/Edit mode-button presentation and grid-button presentation/state only. Lock behavior, prepared locked states, roster data, Edit actions, weapon filters, Version/Update/Download, Old Edit, Cards, persistence, CSV data, Waha routing, and Probable behavior remain unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.103\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

# Retain only the five newest detailed V31 notes.
notes = list(re.finditer(r'\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n', text, re.S))
for note_match in reversed(notes[5:]):
    text = text[:note_match.start()] + text[note_match.end():]

# Final acceptance checks.
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing after writeback')
final_view = html.unescape(vm.group(2))

required_view = [
    "toggle.className='button-standard active-green';",
    "toggle.textContent=p==='view'?'VIEW':'EDIT';",
    "toggle.setAttribute('aria-label',p==='view'?'Switch to Edit':'Switch to View');",
    "toggle.onclick=()=>renderPage(p==='view'?'edit':'view');",
    ".grid-toggle svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round}",
    ".view-grid-toggle{grid-column:16}",
    "gb.className='button-standard grid-toggle'+(p==='view'?' view-grid-toggle':'');",
    "gb.innerHTML='" + grid_svg + "'",
    "const gridOn=grid.classList.contains('grid-on');",
    "gb.classList.toggle('active-green',gridOn);",
    "gb.setAttribute('aria-pressed',gridOn?'true':'false');",
    "grid.classList.toggle('grid-on',on);",
    "activePageMode=p;",
]
for value in required_view:
    if value not in final_view:
        raise SystemExit('V31.104 unified control acceptance failed: ' + value)

for forbidden in [
    "toggle.textContent=p==='view'?'EDIT':'VIEW';",
    "gb.textContent='G'",
    '.view-grid-toggle svg{width:16px;height:16px;',
]:
    if forbidden in final_view:
        raise SystemExit('V31.104 obsolete control behavior remains: ' + forbidden)

required_outer = [
    '<title>WH40k 11th V31.104</title>',
    'The current baseline is WH40k_11th_V31.104;',
    'const APP_VERSION = "31.104";',
    "version: 'V31.104',",
    'CHANGE NOTE - WH40k_11th_V31.104',
]
for value in required_outer:
    if value not in text:
        raise SystemExit('V31.104 acceptance failed: ' + value)

path.write_text(text, encoding='utf-8')
print('Built V31.104: corrected active mode label and shared Grid Mode icon')
