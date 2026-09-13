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
once('<title>WH40k 11th V31.90</title>', '<title>WH40k 11th V31.91</title>', 'title')
once('The current baseline is WH40k_11th_V31.90;', 'The current baseline is WH40k_11th_V31.91;', 'baseline')
once('const APP_VERSION = "31.90";', 'const APP_VERSION = "31.91";', 'APP_VERSION')
once("version: 'V31.90',", "version: 'V31.91',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('New View iframe missing')
view_np = html.unescape(vm.group(2))

# New View row-4 controls: Lock K4, filter M:O, grid icon P4.
old_css = ".grid-toggle{grid-column:13;grid-row:4;z-index:102;align-self:center;justify-self:center;width:var(--std)!important;height:var(--std)!important;padding:0!important}\n.view-filter-toggle{grid-column:14/span 3;grid-row:4;z-index:102;align-self:center;justify-self:center}"
new_css = ".grid-toggle{grid-column:13;grid-row:4;z-index:102;align-self:center;justify-self:center;width:var(--std)!important;height:var(--std)!important;padding:0!important}\n.view-grid-toggle{grid-column:16}\n.view-grid-toggle svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round}\n.new-view-lock-toggle{grid-column:11;grid-row:4;z-index:102;align-self:center;justify-self:center;width:var(--std)!important;height:var(--std)!important;padding:0!important;color:#80d6a3!important;border-color:#80d6a3!important}\n.new-view-lock-toggle.locked{color:#ff9a9a!important;border-color:#ff9a9a!important}\n.new-view-lock-icon{width:18px;height:18px;stroke:currentColor}\n.view-filter-toggle{grid-column:13/span 3;grid-row:4;z-index:102;align-self:center;justify-self:center}"
if view_np.count(old_css) != 1:
    raise SystemExit(f'New View row-4 CSS: expected 1 match, found {view_np.count(old_css)}')
view_np = view_np.replace(old_css, new_css, 1)

# Allow the shared header builder to know whether it is rendering VIEW or EDIT.
old_header_sig = "function addViewHeader(f){"
new_header_sig = "function addViewHeader(f,p){"
if view_np.count(old_header_sig) != 1:
    raise SystemExit(f'New View header signature: expected 1 match, found {view_np.count(old_header_sig)}')
view_np = view_np.replace(old_header_sig, new_header_sig, 1)

header_calls = "addViewHeader(f);"
if view_np.count(header_calls) != 2:
    raise SystemExit(f'New View header calls: expected 2 matches, found {view_np.count(header_calls)}')
view_np = view_np.replace(header_calls, "addViewHeader(f,p);", 2)

# Reuse the old Edit lock SVG geometry and status colors. This is a New View
# visual/state toggle only; it is deliberately not connected to old Edit's
# roster-movement lock or to any processing-freeze behavior.
helper_marker = "function addViewHeader(f,p){"
lock_helpers = r'''let newViewHeaderLocked=false;
function newViewLockIcon(locked){
  const shacklePath=locked
    ? '<path d="M8 10V7a4 4 0 0 1 8 0v3" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" />'
    : '<path d="M8 10V7a4 4 0 0 1 7-2.65" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" />';
  return `<svg class="new-view-lock-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><rect x="6" y="10" width="12" height="10" rx="2" fill="none" stroke="currentColor" stroke-width="2" />${shacklePath}</svg>`;
}
function syncNewViewLockButton(button){
  if(!button)return;
  const locked=Boolean(newViewHeaderLocked);
  const label=locked?'Unlock':'Lock';
  button.classList.toggle('locked',locked);
  button.classList.toggle('unlocked',!locked);
  button.innerHTML=newViewLockIcon(locked);
  button.setAttribute('title',label);
  button.setAttribute('aria-label',label);
  button.setAttribute('aria-pressed',locked?'true':'false');
}
'''
if view_np.count(helper_marker) != 1:
    raise SystemExit('New View lock helper insertion marker missing')
view_np = view_np.replace(helper_marker, lock_helpers + helper_marker, 1)

old_controls = "const gb=document.createElement('button');gb.type='button';gb.className='button-standard grid-toggle';gb.textContent='G';gb.setAttribute('aria-label','Toggle grid');gb.setAttribute('aria-pressed','false');gb.onclick=()=>{const on=!grid.classList.contains('grid-on');grid.classList.toggle('grid-on',on);gb.classList.toggle('active-green',on);gb.setAttribute('aria-pressed',on?'true':'false')};f.appendChild(gb);const fb=document.createElement('button');"
new_controls = "const gb=document.createElement('button');gb.type='button';gb.className='button-standard grid-toggle'+(p==='view'?' view-grid-toggle':'');if(p==='view'){gb.innerHTML='<svg viewBox=\"0 0 24 24\" aria-hidden=\"true\" focusable=\"false\"><rect x=\"4\" y=\"4\" width=\"6\" height=\"6\" rx=\"1\"></rect><rect x=\"14\" y=\"4\" width=\"6\" height=\"6\" rx=\"1\"></rect><rect x=\"4\" y=\"14\" width=\"6\" height=\"6\" rx=\"1\"></rect><rect x=\"14\" y=\"14\" width=\"6\" height=\"6\" rx=\"1\"></rect></svg>'}else{gb.textContent='G'}gb.setAttribute('aria-label','Toggle grid');gb.setAttribute('title','Toggle grid');gb.setAttribute('aria-pressed','false');gb.onclick=()=>{const on=!grid.classList.contains('grid-on');grid.classList.toggle('grid-on',on);gb.classList.toggle('active-green',on);gb.setAttribute('aria-pressed',on?'true':'false')};f.appendChild(gb);if(p==='view'){const lb=document.createElement('button');lb.type='button';lb.className='button-standard new-view-lock-toggle';syncNewViewLockButton(lb);lb.onclick=()=>{newViewHeaderLocked=!newViewHeaderLocked;syncNewViewLockButton(lb)};f.appendChild(lb)}const fb=document.createElement('button');"
if view_np.count(old_controls) != 1:
    raise SystemExit(f'New View header controls: expected 1 match, found {view_np.count(old_controls)}')
view_np = view_np.replace(old_controls, new_controls, 1)

# Write the modified New View document back.
view_srcdoc = html.escape(view_np, quote=True)
text = text[:vm.start(2)] + view_srcdoc + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.91
    Scope: New View header controls only. The grid control moves from the left of the ALL weapon filter to P4 and now uses a four-cell grid icon instead of the letter G. The ALL/SHOOT/MELEE/OTHER filter occupies M4:O4. A lock control is added at K4 using the exact old Edit open/closed lock SVG geometry and the same status colors: open/unlocked green (#80d6a3), closed/locked red (#ff9a9a). The new lock is visual/state-only in this release and is not connected to old Edit's roster-movement lock or processing-freeze behavior. New Edit retains its existing G grid control.
    Risk areas: New View row-4 control placement and icon rendering only. Unit data, weapons, filters, Old Edit, New Edit behavior, Cards, persistence, CSV data, Waha routing, and Probable logic remain unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.90\n'
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
    '.new-view-lock-toggle{grid-column:11;grid-row:4',
    '.view-filter-toggle{grid-column:13/span 3;grid-row:4',
    '.view-grid-toggle{grid-column:16}',
    'function newViewLockIcon(locked)',
    'newViewHeaderLocked=!newViewHeaderLocked',
    "p==='view'?' view-grid-toggle':''",
    "else{gb.textContent='G'}",
    '#80d6a3!important',
    '#ff9a9a!important',
    'M8 10V7a4 4 0 0 1 8 0v3',
    'M8 10V7a4 4 0 0 1 7-2.65',
]
for value in required_view:
    if value not in final_view:
        raise SystemExit('V31.91 New View acceptance failed: ' + value)

required_outer = [
    '<title>WH40k 11th V31.91</title>',
    'const APP_VERSION = "31.91";',
    "version: 'V31.91',",
    'CHANGE NOTE - WH40k_11th_V31.91',
]
for value in required_outer:
    if value not in text:
        raise SystemExit('V31.91 acceptance failed: ' + value)

path.write_text(text, encoding='utf-8')
print('Built V31.91: New View lock K4, filter M-O, grid icon P4')
