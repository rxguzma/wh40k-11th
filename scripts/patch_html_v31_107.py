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
once('<title>WH40k 11th V31.106</title>', '<title>WH40k 11th V31.107</title>', 'title')
once('The current baseline is WH40k_11th_V31.106;', 'The current baseline is WH40k_11th_V31.107;', 'baseline')
once('const APP_VERSION = "31.106";', 'const APP_VERSION = "31.107";', 'APP_VERSION')
once("version: 'V31.106',", "version: 'V31.107',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing')
view_np = html.unescape(vm.group(2))

# Use the already-working Weapon Tag row/box behavior as the template.
weapon_row_match = re.search(r'\.weapon-tags\{[^{}]*\}', view_np)
if not weapon_row_match:
    raise SystemExit('Weapon Tag row CSS missing')
weapon_row = weapon_row_match.group(0)
for required in [
    'display:flex;',
    'align-items:center;',
    'justify-content:flex-start;',
    'gap:var(--gap);',
    'padding:1px 0;',
    'overflow:hidden',
]:
    if required not in weapon_row:
        raise SystemExit('Weapon Tag row template changed unexpectedly: ' + required)

weapon_tag_rules = []
for match in re.finditer(r'\.weapon-tag\{[^{}]*\}', view_np):
    rule = match.group(0)
    if 'flex:0 0 auto' in rule and 'background:var(--btn)' in rule and 'padding:0 8px' in rule:
        weapon_tag_rules.append(rule)
if len(weapon_tag_rules) != 1:
    raise SystemExit(f'Weapon Tag box template: expected 1 match, found {len(weapon_tag_rules)}')
weapon_tag = weapon_tag_rules[0]
for required in [
    'height:var(--std);',
    'flex:0 0 auto;',
    'padding:0 8px;',
    'border:1px solid var(--btnborder);',
    'border-radius:var(--radius);',
    'font:700 var(--meta)/1 Roboto,Arial,sans-serif;',
    'white-space:nowrap;',
]:
    if required not in weapon_tag:
        raise SystemExit('Weapon Tag box template changed unexpectedly: ' + required)

# The Unit Detail row keeps its grid position and visibility behavior, but uses
# the exact same horizontal row geometry as Weapon Tags.
detail_row_match = re.search(r'\.detail-box-row\{[^{}]*\}', view_np)
if not detail_row_match:
    raise SystemExit('Unit Detail row CSS missing')
detail_row = detail_row_match.group(0)

# Normalize only the row-format properties; preserve grid-column/grid-row/z-index/display/height.
for prop, value in [
    ('align-items', 'center'),
    ('justify-content', 'flex-start'),
    ('gap', 'var(--gap)'),
    ('padding', '1px 0'),
    ('overflow', 'hidden'),
]:
    pattern = rf'{re.escape(prop)}:[^;}}]+;?'
    replacement = f'{prop}:{value};'
    if re.search(pattern, detail_row):
        detail_row = re.sub(pattern, replacement, detail_row, count=1)
    else:
        detail_row = detail_row[:-1] + replacement + '}'

view_np = view_np[:detail_row_match.start()] + detail_row + view_np[detail_row_match.end():]

# Remove the old fixed grid-cell widths from Unit Detail boxes. They now size to
# their content exactly like Weapon Tags. Keep their semantic color/cursor rules.
for selector in ['detail-count', 'detail-core-ability', 'detail-waha']:
    pattern = re.compile(rf'(\.{re.escape(selector)}\{{)([^{{}}]*)(\}})')
    match = pattern.search(view_np)
    if not match:
        raise SystemExit(f'{selector} CSS missing')
    body = match.group(2)
    flex_matches = re.findall(r'flex:[^;]+;', body)
    if len(flex_matches) != 1:
        raise SystemExit(f'{selector} flex rule: expected 1 match, found {len(flex_matches)}')
    body = re.sub(r'flex:[^;]+;', 'flex:0 0 auto;', body, count=1)
    replacement = match.group(1) + body + match.group(3)
    view_np = view_np[:match.start()] + replacement + view_np[match.end():]

# Write unified iframe back.
text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.107
    Scope: Standardize the Unit Detail row to the existing working Weapon Tag row behavior in unified New View/Edit. DEEP STRIKE/core ability, Waha, and count boxes no longer use fixed grid-cell widths; they now size to content with the same left-aligned flex-row geometry, gap, padding, and overflow behavior as Weapon Tags. Existing compact box visuals, colors, actions, grid position, row height, and visibility behavior are preserved.
    Risk areas: Unified New View/Edit Unit Detail row sizing/layout only. No Unit, Weapon, Ability, roster, Waha action, lock, Version, persistence, Cards, or Probable logic changes.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.106\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

# Retain only the five newest V31 detailed notes.
notes = list(re.finditer(r'\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n', text, re.S))
for note_match in reversed(notes[5:]):
    text = text[:note_match.start()] + text[note_match.end():]

# Final acceptance checks.
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing after writeback')
final_view = html.unescape(vm.group(2))

final_detail_row_match = re.search(r'\.detail-box-row\{[^{}]*\}', final_view)
if not final_detail_row_match:
    raise SystemExit('Final Unit Detail row CSS missing')
final_detail_row = final_detail_row_match.group(0)
for required in [
    'align-items:center;',
    'justify-content:flex-start;',
    'gap:var(--gap);',
    'padding:1px 0;',
    'overflow:hidden;',
]:
    if required not in final_detail_row:
        raise SystemExit('V31.107 Unit Detail row acceptance failed: ' + required)

for selector in ['detail-count', 'detail-core-ability', 'detail-waha']:
    match = re.search(rf'\.{re.escape(selector)}\{{[^{{}}]*\}}', final_view)
    if not match:
        raise SystemExit(f'Final {selector} CSS missing')
    rule = match.group(0)
    if 'flex:0 0 auto;' not in rule:
        raise SystemExit(f'V31.107 {selector} is not content-sized')
    if 'calc(var(--cell)' in rule:
        raise SystemExit(f'V31.107 {selector} retained fixed grid-cell width')

for required in [
    '.detail-box{height:var(--std);padding:0 8px;border:1px solid var(--btnborder);',
    'font:700 var(--meta)/1 Roboto,Arial,sans-serif;',
    '<title>WH40k 11th V31.107</title>',
    'The current baseline is WH40k_11th_V31.107;',
    'const APP_VERSION = "31.107";',
    "version: 'V31.107',",
    'CHANGE NOTE - WH40k_11th_V31.107',
]:
    if required not in (final_view if required.startswith('.') or required.startswith('font:') else text):
        raise SystemExit('V31.107 acceptance failed: ' + required)

# Protect the unified-page contract.
for forbidden in ['id="newEditPageScreen"', 'id="npEditFrame"', 'parent.getNewEdit']:
    if forbidden in text:
        raise SystemExit('V31.107 regressed retired standalone New Edit: ' + forbidden)
if 'function ensurePersistentGridCells()' not in final_view or 'function clearModeContent()' not in final_view:
    raise SystemExit('V31.107 regressed persistent-grid fast path')

path.write_text(text, encoding='utf-8')
print('Built V31.107: Unit Detail row now follows Weapon Tag row sizing/layout')
