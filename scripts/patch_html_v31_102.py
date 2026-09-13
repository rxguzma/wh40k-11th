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
once('<title>WH40k 11th V31.101</title>', '<title>WH40k 11th V31.102</title>', 'title')
once('The current baseline is WH40k_11th_V31.101;', 'The current baseline is WH40k_11th_V31.102;', 'baseline')
once('const APP_VERSION = "31.101";', 'const APP_VERSION = "31.102";', 'APP_VERSION')
once("version: 'V31.101',", "version: 'V31.102',", 'quality version')

# New View and New Edit are one unified iframe. Standardize Weapon Tag boxes to
# the same compact visual contract as the Unit detail boxes while preserving
# their content-sized width behavior.
view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing')
view_np = html.unescape(vm.group(2))

# Find the standalone Weapon Tag rule rather than touching state selectors such
# as .weapon-tags.weapon-muted .weapon-tag.
tag_rules = []
for match in re.finditer(r'\.weapon-tag\{[^{}]*\}', view_np):
    rule = match.group(0)
    if 'flex:0 0 auto' in rule and 'background:var(--btn)' in rule and 'color:var(--orange)' in rule:
        tag_rules.append((match, rule))
if len(tag_rules) != 1:
    raise SystemExit(f'Weapon Tag base CSS: expected 1 match, found {len(tag_rules)}')
match, old_tag_rule = tag_rules[0]
new_tag_rule = old_tag_rule

if 'padding:0 4px;' not in new_tag_rule:
    raise SystemExit('Weapon Tag padding contract changed unexpectedly')
new_tag_rule = new_tag_rule.replace('padding:0 4px;', 'padding:0 8px;', 1)

if 'border:' in new_tag_rule:
    # A pre-existing border must already be the shared compact-box border.
    if 'border:1px solid var(--btnborder);' not in new_tag_rule:
        raise SystemExit('Weapon Tag has an unexpected pre-existing border')
else:
    new_tag_rule = new_tag_rule.replace('padding:0 8px;', 'padding:0 8px;border:1px solid var(--btnborder);', 1)

old_font = "font:700 var(--meta)/1 'Roboto Condensed',Roboto,Arial,sans-serif;"
new_font = 'font:700 var(--meta)/1 Roboto,Arial,sans-serif;'
if old_font not in new_tag_rule:
    raise SystemExit('Weapon Tag font contract changed unexpectedly')
new_tag_rule = new_tag_rule.replace(old_font, new_font, 1)

view_np = view_np[:match.start()] + new_tag_rule + view_np[match.end():]

# Verify the existing row/box standards before writeback. Weapon Tags remain
# content-sized and the row retains the same standard gap/padding geometry.
required_existing = [
    '.weapon-tags{min-height:var(--cell);display:flex;align-items:center;justify-content:flex-start;gap:var(--gap);padding:1px 0;overflow:hidden}',
    '.detail-box{height:var(--std);padding:0 8px;border:1px solid var(--btnborder);',
    'font:700 var(--meta)/1 Roboto,Arial,sans-serif;',
]
for value in required_existing:
    if value not in view_np:
        raise SystemExit('Existing compact-box contract missing: ' + value)

# Write the unified iframe back.
text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.102
    Scope: Standardize unified New View/Edit Weapon Tag boxes to the same compact visual contract as Unit detail boxes. Weapon Tags now use Roboto 12px bold, 24px standard height, 8px horizontal padding, a 1px button border, the standard 6px radius, shared button background, centered text, and the existing standard row gap. Weapon Tags remain content-sized with no fixed grid spans, so short Tags stay compact and long Tags expand to their text. Existing orange/muted/active semantic states remain unchanged.
    Risk areas: Unified New View/Edit Weapon Tag presentation only. Weapon/Tag data, filtering, selection, Unit detail-box width rules, roster behavior, persistence, Cards, Waha routing, Version controls, and Probable remain unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.101\n'
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
final_tag_rules = []
for css_match in re.finditer(r'\.weapon-tag\{[^{}]*\}', final_view):
    rule = css_match.group(0)
    if 'flex:0 0 auto' in rule and 'background:var(--btn)' in rule and 'color:var(--orange)' in rule:
        final_tag_rules.append(rule)
if len(final_tag_rules) != 1:
    raise SystemExit(f'Final Weapon Tag base CSS: expected 1 match, found {len(final_tag_rules)}')
final_tag = final_tag_rules[0]
for required in [
    'height:var(--std);',
    'flex:0 0 auto;',
    'padding:0 8px;',
    'border:1px solid var(--btnborder);',
    'border-radius:var(--radius);',
    'background:var(--btn);',
    'font:700 var(--meta)/1 Roboto,Arial,sans-serif;',
    'display:inline-flex;',
    'align-items:center;',
    'justify-content:center;',
    'white-space:nowrap;',
]:
    if required not in final_tag:
        raise SystemExit('V31.102 Weapon Tag acceptance failed: ' + required)
for forbidden in [
    'padding:0 4px;',
    "font:700 var(--meta)/1 'Roboto Condensed',Roboto,Arial,sans-serif;",
    "x.style.gridColumn=start+'/span '+span",
]:
    if forbidden in final_view:
        raise SystemExit('V31.102 retained obsolete Weapon Tag behavior: ' + forbidden)

for required in [
    '<title>WH40k 11th V31.102</title>',
    'The current baseline is WH40k_11th_V31.102;',
    'const APP_VERSION = "31.102";',
    "version: 'V31.102',",
    'CHANGE NOTE - WH40k_11th_V31.102',
]:
    if required not in text:
        raise SystemExit('V31.102 release acceptance failed: ' + required)

# Protect the unified-page contract; do not reintroduce standalone New Edit.
for forbidden in ['id="newEditPageScreen"', 'id="npEditFrame"', 'parent.getNewEdit']:
    if forbidden in text:
        raise SystemExit('V31.102 regressed retired standalone New Edit: ' + forbidden)
if 'function ensurePersistentGridCells()' not in final_view or 'function clearModeContent()' not in final_view:
    raise SystemExit('V31.102 regressed persistent-grid fast path')

path.write_text(text, encoding='utf-8')
print('Built V31.102: standardized content-sized Weapon Tag boxes')
