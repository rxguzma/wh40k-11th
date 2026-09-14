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
once('<title>WH40k 11th V31.120</title>', '<title>WH40k 11th V31.121</title>', 'title')
once('The current baseline is WH40k_11th_V31.120;', 'The current baseline is WH40k_11th_V31.121;', 'baseline')
once('const APP_VERSION = "31.120";', 'const APP_VERSION = "31.121";', 'APP_VERSION')
once("version: 'V31.120',", "version: 'V31.121',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing')
view_np = html.unescape(vm.group(2))

# Match the Fix Report label/count typography and spacing to the Version control.
replacements = [
    (
        r'\.new-view-fix-report-title\{[^}]*\}',
        '.new-view-fix-report-title{height:var(--cell);display:grid;grid-template-columns:repeat(16,var(--cell));align-items:center;padding:0;cursor:pointer}'
    ),
    (
        r'\.new-view-fix-report-heading\{[^}]*\}',
        '.new-view-fix-report-heading{grid-column:1/span 8;min-width:0;height:var(--std);display:flex;align-items:center;justify-content:space-between;padding:0 10px;color:var(--text);font-family:Roboto,Arial,sans-serif;font-size:12px;font-weight:700;line-height:1;white-space:nowrap;overflow:hidden}'
    ),
    (
        r'\.new-view-fix-report-count\{[^}]*\}',
        '.new-view-fix-report-count{color:var(--muted);font-family:Roboto,Arial,sans-serif;font-size:12px;font-weight:700;line-height:1;white-space:nowrap;margin-left:8px}'
    ),
]
for pattern, replacement in replacements:
    view_np, n = re.subn(pattern, replacement, view_np, count=1)
    if n != 1:
        raise SystemExit('Fix Report visual anchor missing: ' + pattern)

text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.121
    Scope: Refine the unified New View Fix Report header presentation only. The left Fix Report segment now uses the same 12px/700 Roboto treatment as the Version control, with the item count aligned to the far right of the same eight-column segment like the current version number. Done and Copy All remain unchanged on the right. Collapsed/open behavior, report contents, canonical IDs, Copy All text, persistence, Version positioning, View selection presentation, and all other app behavior remain unchanged.
    Risk areas: Fix Report header typography/alignment only.
  -->

'''
marker = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.120\n'
if text.count(marker) != 1:
    raise SystemExit('V31.120 change-note insertion marker missing')
text = text.replace(marker, note + marker, 1)

# Keep only the five newest detailed V31 change notes.
notes = list(re.finditer(r'\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n', text, re.S))
for match in reversed(notes[5:]):
    text = text[:match.start()] + text[match.end():]

# Acceptance checks.
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing after writeback')
final_view = html.unescape(vm.group(2))
for expected in [
    '.new-view-fix-report-title{height:var(--cell);display:grid;grid-template-columns:repeat(16,var(--cell));align-items:center;padding:0;cursor:pointer}',
    '.new-view-fix-report-heading{grid-column:1/span 8;min-width:0;height:var(--std);display:flex;align-items:center;justify-content:space-between;padding:0 10px;color:var(--text);font-family:Roboto,Arial,sans-serif;font-size:12px;font-weight:700;line-height:1;white-space:nowrap;overflow:hidden}',
    '.new-view-fix-report-count{color:var(--muted);font-family:Roboto,Arial,sans-serif;font-size:12px;font-weight:700;line-height:1;white-space:nowrap;margin-left:8px}',
    "done.type='button';done.className='button-standard';done.textContent='Done';",
    "copy.type='button';copy.className='button-standard active-green';copy.textContent='Copy All';",
]:
    if expected not in final_view:
        raise SystemExit('V31.121 Fix Report acceptance failed: ' + expected)

for expected in [
    '<title>WH40k 11th V31.121</title>',
    'The current baseline is WH40k_11th_V31.121;',
    'const APP_VERSION = "31.121";',
    "version: 'V31.121',",
    'CHANGE NOTE - WH40k_11th_V31.121',
]:
    if expected not in text:
        raise SystemExit('V31.121 release acceptance failed: ' + expected)

path.write_text(text, encoding='utf-8')
print('Built V31.121: Fix Report header matches Version typography and count alignment')
