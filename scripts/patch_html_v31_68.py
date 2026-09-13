from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.67.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')

replacements = [
    ('<title>WH40k 11th V31.67</title>', '<title>WH40k 11th V31.68</title>'),
    ('The current baseline is WH40k_11th_V31.67;', 'The current baseline is WH40k_11th_V31.68;'),
    ('const APP_VERSION = "31.67";', 'const APP_VERSION = "31.68";'),
    ("version: 'V31.67',", "version: 'V31.68',"),
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

# Restore the existing unit-count box for live View rows. The box is created only
# when live data exists and uses the existing .unit-count-grid visual standard.
old_refresh = '''    const name=row.querySelector('.view-unit-name');
    if(name)name.textContent=String(data.name||'');
    [data.m,data.t,data.sv,data.w,data.ld,data.oc].forEach((value,statIndex)=>{const cell=row.querySelector('.s'+(statIndex+1));if(cell)cell.textContent=String(value??'')});'''
new_refresh = '''    const name=row.querySelector('.view-unit-name');
    if(name)name.textContent=String(data.name||'');
    let count=row.querySelector('.unit-count-grid');
    if(!count){count=document.createElement('div');count.className='unit-count-grid';row.appendChild(count)}
    count.textContent='x'+String(data.count??1);
    [data.m,data.t,data.sv,data.w,data.ld,data.oc].forEach((value,statIndex)=>{const cell=row.querySelector('.s'+(statIndex+1));if(cell)cell.textContent=String(value??'')});'''
if np.count(old_refresh) != 1:
    raise SystemExit(f'live Unit row refresh block: expected 1 match, found {np.count(old_refresh)}')
np = np.replace(old_refresh, new_refresh, 1)

for required in [
    "let count=row.querySelector('.unit-count-grid');",
    "count.className='unit-count-grid';",
    "count.textContent='x'+String(data.count??1);",
]:
    if required not in np:
        raise SystemExit('alternate View count check failed: ' + required)

np_srcdoc = html.escape(np, quote=True)
text = text[:match.start(2)] + np_srcdoc + text[match.end(2):]

# The authoritative count already exists in Main: derive it from the active
# roster entry's selected canonical point option through getRosterEntryModelCount.
old_bridge = '''        name: String(model.displayName || (model.unit && model.unit.name) || ""),
        m: String(stats.m ?? ""),'''
new_bridge = '''        name: String(model.displayName || (model.unit && model.unit.name) || ""),
        count: entry && unit ? getRosterEntryModelCount(entry, unit) : 1,
        m: String(stats.m ?? ""),'''
if text.count(old_bridge) != 1:
    raise SystemExit(f'Unit data bridge count insertion: expected 1 match, found {text.count(old_bridge)}')
text = text.replace(old_bridge, new_bridge, 1)

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.68
    Scope: Restore the existing xN unit-count box on the first two alternate-View live Unit rows. The count is no longer prototype/hardcoded data; it comes from the same roster entry and canonical selected point option used by Main through getRosterEntryModelCount(). The existing .unit-count-grid styling is reused unchanged.
    Risk areas: Alternate View first/second Unit count display only. Unit ordering, profile stats, Waha/core-ability row, Weapon filtering/selection, canonical View/Edit/Cards, persistence, and combat behavior are unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.67\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

text = re.sub(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.63\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)

checks = [
    '<title>WH40k 11th V31.68</title>',
    'const APP_VERSION = "31.68";',
    "version: 'V31.68',",
    'count: entry && unit ? getRosterEntryModelCount(entry, unit) : 1,',
    "count.textContent=&#x27;x&#x27;+String(data.count??1);",
    'CHANGE NOTE - WH40k_11th_V31.68',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('acceptance check failed: ' + ', '.join(missing))

out.write_text(text, encoding='utf-8')
print('Built V31.68: live xN unit-count boxes restored from roster point-option count')
