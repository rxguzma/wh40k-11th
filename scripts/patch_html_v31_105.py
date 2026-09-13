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
once('<title>WH40k 11th V31.104</title>', '<title>WH40k 11th V31.105</title>', 'title')
once('The current baseline is WH40k_11th_V31.104;', 'The current baseline is WH40k_11th_V31.105;', 'baseline')
once('const APP_VERSION = "31.104";', 'const APP_VERSION = "31.105";', 'APP_VERSION')
once("version: 'V31.104',", "version: 'V31.105',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing')
view_np = html.unescape(vm.group(2))

grid_svg = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><rect x="4" y="4" width="6" height="6" rx="1"></rect><rect x="14" y="4" width="6" height="6" rx="1"></rect><rect x="4" y="14" width="6" height="6" rx="1"></rect><rect x="14" y="14" width="6" height="6" rx="1"></rect></svg>'
old = "gb.innerHTML='" + grid_svg + "'gb.setAttribute('aria-label','Toggle grid');"
new = "gb.innerHTML='" + grid_svg + "';gb.setAttribute('aria-label','Toggle grid');"
if view_np.count(old) != 1:
    raise SystemExit(f'grid SVG statement separator: expected 1 match, found {view_np.count(old)}')
view_np = view_np.replace(old, new, 1)

text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.105
    Scope: Correct the statement separator in the V31.104 shared Grid Mode icon renderer. This preserves the V31.104 UI behavior exactly: the active local mode is labeled VIEW or EDIT and highlighted green, and both modes use the same four-cell Grid Mode icon with persistent on/off indication.
    Risk areas: Syntax correction in the unified View/Edit grid-button renderer only. No UI placement, state logic, roster data, lock behavior, filters, Edit actions, Version/Update/Download, Cards, persistence, CSV data, Waha routing, or Probable behavior changes.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.104\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

notes = list(re.finditer(r'\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n', text, re.S))
for note_match in reversed(notes[5:]):
    text = text[:note_match.start()] + text[note_match.end():]

vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing after writeback')
final_view = html.unescape(vm.group(2))

required_view = [
    "toggle.className='button-standard active-green';",
    "toggle.textContent=p==='view'?'VIEW':'EDIT';",
    "toggle.onclick=()=>renderPage(p==='view'?'edit':'view');",
    ".grid-toggle svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round}",
    "gb.innerHTML='" + grid_svg + "';gb.setAttribute('aria-label','Toggle grid');",
    "const gridOn=grid.classList.contains('grid-on');",
    "gb.classList.toggle('active-green',gridOn);",
    "gb.setAttribute('aria-pressed',gridOn?'true':'false');",
]
for value in required_view:
    if value not in final_view:
        raise SystemExit('V31.105 unified control acceptance failed: ' + value)

for forbidden in [
    "toggle.textContent=p==='view'?'EDIT':'VIEW';",
    "gb.textContent='G'",
    "'gb.setAttribute('aria-label'",
    "</svg>'gb.setAttribute",
]:
    if forbidden in final_view:
        raise SystemExit('V31.105 invalid/obsolete control behavior remains: ' + forbidden)

required_outer = [
    '<title>WH40k 11th V31.105</title>',
    'The current baseline is WH40k_11th_V31.105;',
    'const APP_VERSION = "31.105";',
    "version: 'V31.105',",
    'CHANGE NOTE - WH40k_11th_V31.105',
]
for value in required_outer:
    if value not in text:
        raise SystemExit('V31.105 acceptance failed: ' + value)

path.write_text(text, encoding='utf-8')
print('Built V31.105: corrected shared Grid Mode renderer syntax')
