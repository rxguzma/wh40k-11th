from pathlib import Path
import re

src = Path('versions/WH40k_11th_V31.78.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


once('<title>WH40k 11th V31.78</title>', '<title>WH40k 11th V31.79</title>', 'title')
once('The current baseline is WH40k_11th_V31.78;', 'The current baseline is WH40k_11th_V31.79;', 'baseline')
once('const APP_VERSION = "31.78";', 'const APP_VERSION = "31.79";', 'APP_VERSION')
once("version: 'V31.78',", "version: 'V31.79',", 'quality version')

# The legacy/global title renderer was still independently appending Cards VP
# to its points string. Remove that VP contribution so it cannot bleed through
# behind/alongside the New View title, whose title contract is owned by New Edit.
old_points = '      const pointsText = `${getRosterPoints(roster)} pts - ${getCardsTotalVpForRoster(roster)} VPs`;'
new_points = '      const pointsText = `${getRosterPoints(roster)} pts`;'
once(old_points, new_points, 'legacy/global title VP removal')

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.79
    Scope: Remove the remaining VP value from the legacy/global title renderer. Its title points string now contains roster points only, preventing Cards VP from appearing behind or alongside the New View title. New View title data remains sourced from New Edit as established in V31.78. No Unit/Weapon linkage changes are made.
    Risk areas: Global title points text only. New View/New Edit title linkage, Unit/Weapon data sources, Cards scoring itself, persistence, CSV data, Waha routing, and Probable are unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.78\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.74\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

for forbidden in [
    'const pointsText = `${getRosterPoints(roster)} pts - ${getCardsTotalVpForRoster(roster)} VPs`;',
]:
    if forbidden in text:
        raise SystemExit('VP title dependency remains: ' + forbidden)

for required in [
    '<title>WH40k 11th V31.79</title>',
    'const APP_VERSION = "31.79";',
    "version: 'V31.79',",
    'const pointsText = `${getRosterPoints(roster)} pts`;',
    'CHANGE NOTE - WH40k_11th_V31.79',
]:
    if required not in text:
        raise SystemExit('acceptance check failed: ' + required)

out.write_text(text, encoding='utf-8')
print('Built V31.79: removed remaining VP from legacy/global title renderer')
