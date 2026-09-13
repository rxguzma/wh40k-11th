from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.74.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def once(old, new, label):
    global text
    n = text.count(old)
    if n != 1:
        raise SystemExit(f'{label}: expected 1 match, found {n}')
    text = text.replace(old, new, 1)


once('<title>WH40k 11th V31.74</title>', '<title>WH40k 11th V31.75</title>', 'title')
once('The current baseline is WH40k_11th_V31.74;', 'The current baseline is WH40k_11th_V31.75;', 'baseline')
once('const APP_VERSION = "31.74";', 'const APP_VERSION = "31.75";', 'APP_VERSION')
once("version: 'V31.74',", "version: 'V31.75',", 'quality version')

edit_pat = re.compile(r'(<iframe id="npEditFrame" class="np-view-frame" title="New Edit" srcdoc=")(.*?)("></iframe>)', re.S)
em = edit_pat.search(text)
if not em:
    raise SystemExit('New Edit iframe missing')
edit_np = html.unescape(em.group(2))

old_refresh = r'''function refreshNewEditUnitsFromLegacy(){
  for(let index=0;index<2;index++){
    const row=grid.querySelector(index===0?'.edit-unit-row-first':'.edit-unit-row-second');
    if(!row)continue;
    const data=legacyUnitForNewEdit(index);
    if(!data){row.style.display='none';continue}
    row.style.display='grid';
    const name=row.querySelector('.edit-unit-name');
    if(name)name.textContent=String(data.name||'');
  }
  return Boolean(legacyUnitForNewEdit(0)||legacyUnitForNewEdit(1));
}'''
new_refresh = r'''function refreshNewEditUnitsFromLegacy(){
  const start=typeof FIRST_UNIT_ROW==='number'?FIRST_UNIT_ROW:7;
  for(let index=0;index<2;index++){
    const row=grid.querySelector(index===0?'.edit-unit-row-first':'.edit-unit-row-second');
    if(!row)continue;
    const data=legacyUnitForNewEdit(index);
    if(!data){row.style.display='none';continue}
    row.style.gridRow=String(start+index);
    row.style.display='grid';
    const name=row.querySelector('.edit-unit-name');
    if(name)name.textContent=String(data.name||'');
  }
  return Boolean(legacyUnitForNewEdit(0)||legacyUnitForNewEdit(1));
}'''
if edit_np.count(old_refresh) != 1:
    raise SystemExit(f'New Edit refresh function: expected 1 match, found {edit_np.count(old_refresh)}')
edit_np = edit_np.replace(old_refresh, new_refresh, 1)

# New View already uses FIRST_UNIT_ROW and compact collapsed positioning.
# New Edit now renders its two visible Unit rows consecutively from that same
# starting row, instead of leaving Unit 2 on its dormant authored row 20.
for required in [
    "const start=typeof FIRST_UNIT_ROW==='number'?FIRST_UNIT_ROW:7;",
    "row.style.gridRow=String(start+index);",
    "window.refreshNewEditUnitsFromLegacy=refreshNewEditUnitsFromLegacy;",
]:
    if required not in edit_np:
        raise SystemExit('New Edit compact-layout check failed: ' + required)

text = text[:em.start(2)] + html.escape(edit_np, quote=True) + text[em.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.75
    Scope: Fix the New Edit Unit list layout so its visible Unit rows use the same compact displayed positions as the collapsed New View list. New View already dynamically compacts Unit 2 from its dormant authored row to the row immediately below Unit 1; New Edit now does the same by positioning its two live Unit rows consecutively from FIRST_UNIT_ROW. This removes the large empty gap while preserving the existing Old Edit/model -> New Edit -> New View data dependency. No additional Edit functionality is migrated.
    Risk areas: New Edit visible Unit row positioning only. Unit data/order, New View layout and expansion behavior, legacy Edit, Cards, persistence, Waha routing, combat behavior, and CSV data remain unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.74\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.70\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

checks = [
    '<title>WH40k 11th V31.75</title>',
    'const APP_VERSION = "31.75";',
    "version: 'V31.75',",
    'id="npEditFrame" class="np-view-frame" title="New Edit"',
    'row.style.gridRow=String(start+index);',
    'CHANGE NOTE - WH40k_11th_V31.75',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('acceptance check failed: ' + ', '.join(missing))

out.write_text(text, encoding='utf-8')
print('Built V31.75: compact New Edit Unit rows aligned to collapsed New View')
