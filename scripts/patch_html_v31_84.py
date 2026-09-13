from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.83.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


once('<title>WH40k 11th V31.83</title>', '<title>WH40k 11th V31.84</title>', 'title')
once('The current baseline is WH40k_11th_V31.83;', 'The current baseline is WH40k_11th_V31.84;', 'baseline')
once('const APP_VERSION = "31.83";', 'const APP_VERSION = "31.84";', 'APP_VERSION')
once("version: 'V31.83',", "version: 'V31.84',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
edit_pat = re.compile(r'(<iframe id="npEditFrame" class="np-view-frame" title="New Edit" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
em = edit_pat.search(text)
if not vm or not em:
    raise SystemExit('New View/New Edit iframe missing')
view_np = html.unescape(vm.group(2))
edit_np = html.unescape(em.group(2))


def fix_weapon_tag_sizing(doc, label):
    old_row = '.weapon-tags{min-height:var(--cell);grid-template-columns:repeat(16,var(--cell));padding:0;overflow:hidden}'
    new_row = '.weapon-tags{min-height:var(--cell);display:flex;align-items:center;justify-content:flex-start;gap:var(--gap);padding:1px 0;overflow:hidden}'
    row_count = doc.count(old_row)
    if row_count != 1:
        raise SystemExit(f'{label} weapon tag row CSS: expected 1 match, found {row_count}')
    doc = doc.replace(old_row, new_row, 1)

    old_tag = ".weapon-tag{height:var(--std);width:calc(100% - var(--gap));justify-self:center;padding:0 4px;display:inline-flex;align-items:center;justify-content:center;border-radius:var(--radius);background:var(--btn);color:var(--orange);font:700 var(--meta)/1 'Roboto Condensed',Roboto,Arial,sans-serif;white-space:nowrap;overflow:hidden}"
    new_tag = ".weapon-tag{height:var(--std);flex:0 0 auto;padding:0 4px;display:inline-flex;align-items:center;justify-content:center;border-radius:var(--radius);background:var(--btn);color:var(--orange);font:700 var(--meta)/1 'Roboto Condensed',Roboto,Arial,sans-serif;white-space:nowrap;overflow:hidden}"
    tag_count = doc.count(old_tag)
    if tag_count != 1:
        raise SystemExit(f'{label} weapon tag CSS: expected 1 match, found {tag_count}')
    doc = doc.replace(old_tag, new_tag, 1)

    display_count = doc.count("tagRow.style.display='grid';")
    if display_count < 1:
        raise SystemExit(f'{label} live weapon tag display: expected at least 1 match')
    doc = doc.replace("tagRow.style.display='grid';", "tagRow.style.display='flex';")

    old_builder = "tags.forEach(([t,start,span])=>{const x=document.createElement('span');x.className='weapon-tag';x.textContent=t;x.style.gridColumn=start+'/span '+span;r.appendChild(x)})"
    new_builder = "tags.forEach(([t])=>{const x=document.createElement('span');x.className='weapon-tag';x.textContent=t;r.appendChild(x)})"
    builder_count = doc.count(old_builder)
    if builder_count != 1:
        raise SystemExit(f'{label} fixed-span tag builder: expected 1 match, found {builder_count}')
    doc = doc.replace(old_builder, new_builder, 1)

    return doc


view_np = fix_weapon_tag_sizing(view_np, 'New View')
edit_np = fix_weapon_tag_sizing(edit_np, 'New Edit')

text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]
em = edit_pat.search(text)
if not em:
    raise SystemExit('New Edit iframe missing after New View writeback')
text = text[:em.start(2)] + html.escape(edit_np, quote=True) + text[em.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.84
    Scope: Make Weapon Tag boxes content-sized in New View and New Edit instead of assigning fixed grid-cell spans per Tag. Tag rows now lay out left-to-right with the existing gap, height, padding, typography, colors, and one-line labels; short Tags remain compact and long Tags expand enough to display their full text. The live Weapon Tag renderer no longer forces grid display, and the authored placeholder Tag builder no longer applies per-Tag gridColumn spans. No Weapon data, Tag data, filtering, selection, profile, roster, Cards, persistence, or Probable behavior changes.
    Risk areas: New View/New Edit Weapon Tag row layout only.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.83\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.79\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

vm = view_pat.search(text)
em = edit_pat.search(text)
if not vm or not em:
    raise SystemExit('final iframe verification failed')
final_view = html.unescape(vm.group(2))
final_edit = html.unescape(em.group(2))

for doc, label in [(final_view, 'New View'), (final_edit, 'New Edit')]:
    for required in [
        '.weapon-tags{min-height:var(--cell);display:flex;align-items:center;justify-content:flex-start;gap:var(--gap);padding:1px 0;overflow:hidden}',
        '.weapon-tag{height:var(--std);flex:0 0 auto;padding:0 4px;',
        "tagRow.style.display='flex';",
        "tags.forEach(([t])=>{const x=document.createElement('span');x.className='weapon-tag';x.textContent=t;r.appendChild(x)})",
    ]:
        if required not in doc:
            raise SystemExit(f'{label} auto-size acceptance failed: {required}')
    for forbidden in [
        '.weapon-tags{min-height:var(--cell);grid-template-columns:repeat(16,var(--cell));padding:0;overflow:hidden}',
        '.weapon-tag{height:var(--std);width:calc(100% - var(--gap));justify-self:center;',
        "tagRow.style.display='grid';",
        "x.style.gridColumn=start+'/span '+span",
    ]:
        if forbidden in doc:
            raise SystemExit(f'{label} still contains fixed-span Weapon Tag behavior: {forbidden}')

if 'parent.getNewEditUnitData(index)' not in final_view:
    raise SystemExit('New View Unit source changed unexpectedly')

for required in [
    '<title>WH40k 11th V31.84</title>',
    'const APP_VERSION = "31.84";',
    "version: 'V31.84',",
    'CHANGE NOTE - WH40k_11th_V31.84',
]:
    if required not in text:
        raise SystemExit('version acceptance check failed: ' + required)

out.write_text(text, encoding='utf-8')
print('Built V31.84: content-sized Weapon Tag boxes in New View and New Edit')
