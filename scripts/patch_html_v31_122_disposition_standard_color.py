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
once('<title>WH40k 11th V31.121</title>', '<title>WH40k 11th V31.122</title>', 'title')
once('The current baseline is WH40k_11th_V31.121;', 'The current baseline is WH40k_11th_V31.122;', 'baseline')
once('const APP_VERSION = "31.121";', 'const APP_VERSION = "31.122";', 'APP_VERSION')
once("version: 'V31.121',", "version: 'V31.122',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing')
view_np = html.unescape(vm.group(2))

# Priority Assets uses top-summary-disposition. Match its text color to the
# standard muted header color already used by the Detachment line (e.g. Wreckas).
if '.top-detachments{' not in view_np or 'color:var(--muted)' not in view_np:
    raise SystemExit('Standard Detachment muted-color contract missing')

pattern = re.compile(r'(\.top-summary-disposition\{[^{}]*?color:)#[0-9a-fA-F]{6}([^{}]*\})')
view_np, count = pattern.subn(r'\1var(--muted)\2', view_np, count=1)
if count != 1:
    raise SystemExit(f'top-summary-disposition color: expected 1 match, found {count}')

text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.122
    Scope: Change the New View disposition text (for example, Priority Assets) from the active green treatment to the same standard muted text color used by the Detachment line (for example, Wreckas). Layout, typography, spacing, wording, and all behavior remain unchanged.
    Risk areas: New View header disposition text color only.
  -->

'''
marker = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.121\n'
if text.count(marker) != 1:
    raise SystemExit('V31.121 change-note insertion marker missing')
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

summary_rules = re.findall(r'\.top-summary-disposition\{[^{}]*\}', final_view)
if len(summary_rules) != 1:
    raise SystemExit(f'Expected one top-summary-disposition rule, found {len(summary_rules)}')
if 'color:var(--muted)' not in summary_rules[0]:
    raise SystemExit('Disposition did not inherit the standard muted color')
if '#80d6a3' in summary_rules[0]:
    raise SystemExit('Old green disposition color remains')

for expected in [
    '<title>WH40k 11th V31.122</title>',
    'The current baseline is WH40k_11th_V31.122;',
    'const APP_VERSION = "31.122";',
    "version: 'V31.122',",
    'CHANGE NOTE - WH40k_11th_V31.122',
]:
    if expected not in text:
        raise SystemExit('V31.122 release acceptance failed: ' + expected)

path.write_text(text, encoding='utf-8')
print('Built V31.122: disposition text now uses standard muted header color')
