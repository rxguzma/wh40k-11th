from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.62.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')

replacements = [
    ('<title>WH40k 11th V31.62</title>', '<title>WH40k 11th V31.63</title>'),
    ('The current baseline is WH40k_11th_V31.62;', 'The current baseline is WH40k_11th_V31.63;'),
    ('const APP_VERSION = "31.62";', 'const APP_VERSION = "31.63";'),
    ("version: 'V31.62',", "version: 'V31.63',"),
]
for old, new in replacements:
    if old not in text:
        raise SystemExit('version marker missing: ' + old)
    text = text.replace(old, new, 1)

frame_pattern = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
match = frame_pattern.search(text)
if not match:
    raise SystemExit('alternate View iframe not found')
np = html.unescape(match.group(2))

# The first wired View row is no longer Nazdreg-specific. It asks the parent for
# the first real unit in current Edit/roster order.
old_parent_call = "parent&&typeof parent.getAlternateViewNazdregData==='function'?parent.getAlternateViewNazdregData():null"
new_parent_call = "parent&&typeof parent.getAlternateViewPrimaryUnitData==='function'?parent.getAlternateViewPrimaryUnitData():null"
if np.count(old_parent_call) != 1:
    raise SystemExit(f'primary unit parent call: expected 1 match, found {np.count(old_parent_call)}')
np = np.replace(old_parent_call, new_parent_call, 1)

# Remove visible Nazdreg fallback text from the generic first row.
np = np.replace("if(name)name.textContent=String(data.name||'Nazdreg');", "if(name)name.textContent=String(data.name||'');", 1)
np = np.replace("addViewUnit(f,'view-unit-row-first','Nazdreg','',['','','','','','']);", "addViewUnit(f,'view-unit-row-first','','',['','','','','','']);", 1)

np_srcdoc = html.escape(np, quote=True)
text = text[:match.start(2)] + np_srcdoc + text[match.end(2):]

# Replace the hardcoded Nazdreg lookup with the first valid roster model. The
# getRosterEntryModels order is the same order used by Edit, so reordering Edit
# changes which unit occupies the first wired View row.
lookup_pattern = re.compile(
    r'''    window\.getAlternateViewNazdregData = function\(\) \{\n      const roster = appEditMode && viewEditRosterDraft \? getViewEditRoster\(\) : getActiveRoster\(\);\n      const models = getRosterEntryModels\(roster\);\n      const normalize = value => String\(value \|\| ""\)\.trim\(\)\.toLowerCase\(\)\.replace\(/\[\^a-z0-9\]\+/g, ""\);\n      const model = models\.find\(item => \{\n        if \(!item \|\| item\.isSpacer \|\| item\.isNote \|\| item\.isDeleted \|\| item\.isMissingUnit\) return false;\n        const candidates = \[\n          item\.displayName,\n          item\.unit && item\.unit\.name,\n          item\.entry && item\.entry\.unitId,\n          item\.unit && item\.unit\.unitId\n        \]\.map\(normalize\)\.filter\(Boolean\);\n        return candidates\.some\(value => value === "nazdreg" \|\| value\.endsWith\("nazdreg"\)\);\n      \}\);\n      if \(!model\) return null;''',
    re.S,
)
replacement = '''    window.getAlternateViewPrimaryUnitData = function() {\n      const roster = appEditMode && viewEditRosterDraft ? getViewEditRoster() : getActiveRoster();\n      const models = getRosterEntryModels(roster);\n      const model = models.find(item => item && !item.isSpacer && !item.isNote && !item.isDeleted && !item.isMissingUnit);\n      if (!model) return null;'''
text, count = lookup_pattern.subn(replacement, text, count=1)
if count != 1:
    raise SystemExit(f'primary unit lookup: expected 1 match, found {count}')

# Remove the old hardcoded display-name fallback in the parent return object.
old_name = 'name: String(model.displayName || (model.unit && model.unit.name) || "Nazdreg"),'
new_name = 'name: String(model.displayName || (model.unit && model.unit.name) || ""),'
if text.count(old_name) != 1:
    raise SystemExit(f'primary unit name fallback: expected 1 match, found {text.count(old_name)}')
text = text.replace(old_name, new_name, 1)

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.63
    Scope: Remove Nazdreg-specific first-row lookup from alternate View. The first wired View row now binds to the first real unit returned in current Edit/roster order, including that unit's live name, stats, Waha link, Weapons, filtering, expansion, and Weapon-selection behavior. Reordering units in Edit therefore changes which unit is shown in the first wired row. No additional unit rows are wired in this version.
    Risk areas: Alternate View first-unit data selection only. Existing first-row interaction/styling, canonical View/Edit/Cards, persistence, and combat behavior are unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.62\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

text = re.sub(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.58\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)

checks = [
    '<title>WH40k 11th V31.63</title>',
    'const APP_VERSION = "31.63";',
    "version: 'V31.63',",
    'window.getAlternateViewPrimaryUnitData = function()',
    'const model = models.find(item => item && !item.isSpacer && !item.isNote && !item.isDeleted && !item.isMissingUnit);',
    'parent.getAlternateViewPrimaryUnitData',
    'CHANGE NOTE - WH40k_11th_V31.63',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('acceptance check failed: ' + ', '.join(missing))
if 'value === "nazdreg"' in text or 'value.endsWith("nazdreg")' in text:
    raise SystemExit('hardcoded Nazdreg lookup still present')

out.write_text(text, encoding='utf-8')
print('Built V31.63: first wired alternate-View unit follows Edit order')
