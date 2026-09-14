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
once('<title>WH40k 11th V31.108</title>', '<title>WH40k 11th V31.109</title>', 'title')
once('The current baseline is WH40k_11th_V31.108;', 'The current baseline is WH40k_11th_V31.109;', 'baseline')
once('const APP_VERSION = "31.108";', 'const APP_VERSION = "31.109";', 'APP_VERSION')
once("version: 'V31.108',", "version: 'V31.109',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing')
view_np = html.unescape(vm.group(2))

# Put the shared Grid Mode control in the exact same P4 location in both modes.
old_css = '.grid-toggle{grid-column:13;grid-row:4;z-index:102;align-self:center;justify-self:center;width:var(--std)!important;height:var(--std)!important;padding:0!important}'
new_css = '.grid-toggle{grid-column:16;grid-row:4;z-index:102;align-self:center;justify-self:center;width:var(--std)!important;height:var(--std)!important;padding:0!important}'
if view_np.count(old_css) != 1:
    raise SystemExit(f'Grid base position: expected 1 match, found {view_np.count(old_css)}')
view_np = view_np.replace(old_css, new_css, 1)

text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.109
    Scope: Put the shared Grid Mode button in the exact same location in unified VIEW and EDIT. The base grid control now occupies P4 in both modes; VIEW keeps its existing P4 placement and EDIT moves from M4 to P4. The existing four-cell icon, green on/off indication, click behavior, and VIEW/EDIT active-mode labels remain unchanged.
    Risk areas: Unified New View/Edit Grid Mode placement only. No roster data, Unit Detail, lock behavior, weapon filters, Edit actions, Version/Update/Download, Cards, persistence, CSV data, Waha routing, or Probable behavior changes.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.108\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

notes = list(re.finditer(r'\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n', text, re.S))
for match in reversed(notes[5:]):
    text = text[:match.start()] + text[match.end():]

# Acceptance checks.
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing after writeback')
final_view = html.unescape(vm.group(2))
required = [
    '.grid-toggle{grid-column:16;grid-row:4;',
    '.view-grid-toggle{grid-column:16}',
    ".grid-toggle svg{width:16px;height:16px;",
    "toggle.className='button-standard active-green';",
    "toggle.textContent=p==='view'?'VIEW':'EDIT';",
    "gb.innerHTML='<svg viewBox=\"0 0 24 24\"",
]
for value in required:
    if value not in final_view:
        raise SystemExit('V31.109 acceptance failed: ' + value)
if '.grid-toggle{grid-column:13;grid-row:4;' in final_view:
    raise SystemExit('V31.109 old Edit grid position remains')
for value in [
    '<title>WH40k 11th V31.109</title>',
    'The current baseline is WH40k_11th_V31.109;',
    'const APP_VERSION = "31.109";',
    "version: 'V31.109',",
    'CHANGE NOTE - WH40k_11th_V31.109',
]:
    if value not in text:
        raise SystemExit('V31.109 outer acceptance failed: ' + value)

path.write_text(text, encoding='utf-8')
print('Built V31.109: Grid Mode button at P4 in both VIEW and EDIT')
