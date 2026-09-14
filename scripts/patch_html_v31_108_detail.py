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


once('<title>WH40k 11th V31.107</title>', '<title>WH40k 11th V31.108</title>', 'title')
once('The current baseline is WH40k_11th_V31.107;', 'The current baseline is WH40k_11th_V31.108;', 'baseline')
once('const APP_VERSION = "31.107";', 'const APP_VERSION = "31.108";', 'APP_VERSION')
once("version: 'V31.107',", "version: 'V31.108',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing')
view_np = html.unescape(vm.group(2))

# Preserve V31.107 scrolling and use the existing Weapon Tag row/box contract.
for required in [
    'function syncNewViewFrameHeight()',
    '.weapon-tags{min-height:var(--cell);display:flex;align-items:center;justify-content:flex-start;gap:var(--gap);padding:1px 0;overflow:hidden}',
    'flex:0 0 auto;padding:0 8px;border:1px solid var(--btnborder);',
    'font:700 var(--meta)/1 Roboto,Arial,sans-serif;',
    '.detail-box{height:var(--std);padding:0 8px;border:1px solid var(--btnborder);',
]:
    if required not in view_np:
        raise SystemExit('V31.108 baseline contract missing: ' + required)

# Unit Detail row already uses the same alignment/gap/padding as Weapon Tags.
# Add the same overflow behavior without changing its grid position or visibility.
row_matches = []
for match in re.finditer(r'\.detail-box-row\{[^{}]*\}', view_np):
    rule = match.group(0)
    if 'grid-column:1/span 16' in rule and 'gap:var(--gap)' in rule:
        row_matches.append((match, rule))
if len(row_matches) != 1:
    raise SystemExit(f'Unit Detail row CSS: expected 1 match, found {len(row_matches)}')
match, rule = row_matches[0]
for required in ['align-items:center;', 'justify-content:flex-start;', 'gap:var(--gap);', 'padding:1px 0']:
    if required not in rule:
        raise SystemExit('Unit Detail row contract changed unexpectedly: ' + required)
if 'overflow:hidden' not in rule:
    rule = rule[:-1] + ('overflow:hidden}' if rule.endswith(';}') else ';overflow:hidden}')
view_np = view_np[:match.start()] + rule + view_np[match.end():]

# Remove only the old fixed-width rule for each box type. Some selectors have
# additional state rules; those are intentionally left untouched.
for selector in ['detail-count', 'detail-core-ability', 'detail-waha']:
    candidates = []
    for match in re.finditer(rf'\.{re.escape(selector)}\{{[^{{}}]*\}}', view_np):
        rule = match.group(0)
        if 'flex:' in rule and 'calc(var(--cell)' in rule:
            candidates.append((match, rule))
    if len(candidates) != 1:
        raise SystemExit(f'{selector} fixed-width rule: expected 1 match, found {len(candidates)}')
    match, rule = candidates[0]
    rule = re.sub(r'flex:[^;]+;', 'flex:0 0 auto;', rule, count=1)
    view_np = view_np[:match.start()] + rule + view_np[match.end():]

text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.108
    Scope: Make the Unit Detail row use the existing working Weapon Tag row/box behavior in unified New View/Edit. DEEP STRIKE/core ability, Waha, and count boxes no longer use fixed 2/3-grid-cell widths; they now size to their content like Weapon Tags. The row keeps its existing position, height, visibility logic, colors, actions, and standard gap/padding, with the same overflow behavior as Weapon Tags.
    Risk areas: Unified New View/Edit Unit Detail row sizing only. V31.107 scrolling behavior is preserved. No Unit, Weapon, Ability, roster, Waha action, lock, Version, persistence, Cards, or Probable logic changes.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.107\n'
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

final_rows = [m.group(0) for m in re.finditer(r'\.detail-box-row\{[^{}]*\}', final_view) if 'grid-column:1/span 16' in m.group(0) and 'gap:var(--gap)' in m.group(0)]
if len(final_rows) != 1 or 'overflow:hidden' not in final_rows[0]:
    raise SystemExit('V31.108 Unit Detail row acceptance failed')

for selector in ['detail-count', 'detail-core-ability', 'detail-waha']:
    rules = [m.group(0) for m in re.finditer(rf'\.{re.escape(selector)}\{{[^{{}}]*\}}', final_view)]
    if not any('flex:0 0 auto;' in rule for rule in rules):
        raise SystemExit(f'V31.108 {selector} is not content-sized')
    if any('flex:' in rule and 'calc(var(--cell)' in rule for rule in rules):
        raise SystemExit(f'V31.108 {selector} retained fixed grid-cell width')

for required in [
    'function syncNewViewFrameHeight()',
    '.weapon-tags{min-height:var(--cell);display:flex;align-items:center;justify-content:flex-start;gap:var(--gap);padding:1px 0;overflow:hidden}',
    '.detail-box{height:var(--std);padding:0 8px;border:1px solid var(--btnborder);',
    'function ensurePersistentGridCells()',
    'function clearModeContent()',
]:
    if required not in final_view:
        raise SystemExit('V31.108 iframe acceptance failed: ' + required)

for required in [
    '<title>WH40k 11th V31.108</title>',
    'The current baseline is WH40k_11th_V31.108;',
    'const APP_VERSION = "31.108";',
    "version: 'V31.108',",
    'CHANGE NOTE - WH40k_11th_V31.108',
]:
    if required not in text:
        raise SystemExit('V31.108 release acceptance failed: ' + required)

for forbidden in ['id="newEditPageScreen"', 'id="npEditFrame"', 'parent.getNewEdit']:
    if forbidden in text:
        raise SystemExit('V31.108 regressed retired standalone New Edit: ' + forbidden)

path.write_text(text, encoding='utf-8')
print('Built V31.108: Unit Detail row now uses content-sized Weapon Tag behavior')
