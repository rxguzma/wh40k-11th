from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.82.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


once('<title>WH40k 11th V31.82</title>', '<title>WH40k 11th V31.83</title>', 'title')
once('The current baseline is WH40k_11th_V31.82;', 'The current baseline is WH40k_11th_V31.83;', 'baseline')
once('const APP_VERSION = "31.82";', 'const APP_VERSION = "31.83";', 'APP_VERSION')
once("version: 'V31.82',", "version: 'V31.83',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
edit_pat = re.compile(r'(<iframe id="npEditFrame" class="np-view-frame" title="New Edit" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
em = edit_pat.search(text)
if not vm or not em:
    raise SystemExit('New View/New Edit iframe missing')
view_np = html.unescape(vm.group(2))
edit_np = html.unescape(em.group(2))


def fix_detail_widths(doc, label):
    old_row = '.detail-box-row{grid-column:1/span 16;grid-row:8;z-index:3;display:none;align-items:center;gap:var(--gap);height:var(--cell);min-width:0;padding:1px 0}'
    new_row = '.detail-box-row{grid-column:1/span 16;grid-row:8;z-index:3;display:none;align-items:center;justify-content:flex-start;gap:var(--gap);height:var(--cell);min-width:0;padding:1px 0}'
    if doc.count(old_row) != 1:
        raise SystemExit(f'{label} detail row CSS: expected 1 match, found {doc.count(old_row)}')
    doc = doc.replace(old_row, new_row, 1)

    old_tag = '.detail-core-ability{flex:1 1 0;min-width:0;color:var(--orange)}'
    new_tag = '.detail-core-ability{flex:0 0 calc(var(--cell)*3 - var(--gap));min-width:0;color:var(--orange)}'
    if doc.count(old_tag) != 1:
        raise SystemExit(f'{label} detail tag CSS: expected 1 match, found {doc.count(old_tag)}')
    doc = doc.replace(old_tag, new_tag, 1)
    return doc


view_np = fix_detail_widths(view_np, 'New View')
edit_np = fix_detail_widths(edit_np, 'New Edit')

text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]
em = edit_pat.search(text)
if not em:
    raise SystemExit('New Edit iframe missing after New View writeback')
text = text[:em.start(2)] + html.escape(edit_np, quote=True) + text[em.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.83
    Scope: Fix the V31.82 Unit detail-row width regression in New Edit and New View. Hiding singleton x1 in New View no longer causes the remaining Unit/core tag box to stretch across the vacated row. Quantity remains a fixed two-cell box when shown, each Unit/core tag remains its normal fixed three-cell standard box, and Waha remains the final fixed three-cell standard box. Detail boxes stay left-aligned in sequence. No data-source, singleton-count, Waha action, Weapon, title, or legacy migration behavior changes.
    Risk areas: New Edit/New View Unit detail-row box sizing only.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.82\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.78\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
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
        'justify-content:flex-start',
        '.detail-count{flex:0 0 calc(var(--cell)*2 - var(--gap));',
        '.detail-core-ability{flex:0 0 calc(var(--cell)*3 - var(--gap));',
        '.detail-waha{flex:0 0 calc(var(--cell)*3 - var(--gap));',
        "detailRow.insertBefore(tag,waha||null);",
    ]:
        if required not in doc:
            raise SystemExit(f'{label} fixed-width detail acceptance failed: {required}')
    if '.detail-core-ability{flex:1 1 0;' in doc:
        raise SystemExit(f'{label} still contains stretching detail tag CSS')

if "HIDE_SINGLETON_COUNT&&countValue===1&&countOptionCount===1" not in final_view:
    raise SystemExit('New View singleton x1 rule changed unexpectedly')
if 'parent.getNewEditUnitData(index)' not in final_view:
    raise SystemExit('New View Unit source changed unexpectedly')

for required in [
    '<title>WH40k 11th V31.83</title>',
    'const APP_VERSION = "31.83";',
    "version: 'V31.83',",
    'CHANGE NOTE - WH40k_11th_V31.83',
]:
    if required not in text:
        raise SystemExit('version acceptance check failed: ' + required)

out.write_text(text, encoding='utf-8')
print('Built V31.83: fixed-width Unit detail boxes; no stretching when x1 is hidden')
