from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.81.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


once('<title>WH40k 11th V31.81</title>', '<title>WH40k 11th V31.82</title>', 'title')
once('The current baseline is WH40k_11th_V31.81;', 'The current baseline is WH40k_11th_V31.82;', 'baseline')
once('const APP_VERSION = "31.81";', 'const APP_VERSION = "31.82";', 'APP_VERSION')
once("version: 'V31.81',", "version: 'V31.82',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
edit_pat = re.compile(r'(<iframe id="npEditFrame" class="np-view-frame" title="New Edit" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
em = edit_pat.search(text)
if not vm or not em:
    raise SystemExit('New View/New Edit iframe missing')
view_np = html.unescape(vm.group(2))
edit_np = html.unescape(em.group(2))


def patch_detail_doc(doc, hide_singleton, label):
    css_anchor = ".detail-row-muted{color:rgba(154,160,166,.5)!important;opacity:1!important}"
    css_add = css_anchor + "\n" + (
        ".detail-box-row{grid-column:1/span 16;grid-row:8;z-index:3;display:none;align-items:center;gap:var(--gap);height:var(--cell);min-width:0;padding:1px 0}"
        ".detail-box{height:var(--std);padding:0 8px;border:1px solid var(--btnborder);border-radius:var(--radius);background:var(--btn);color:var(--text);font:700 var(--meta)/1 Roboto,Arial,sans-serif;display:inline-flex;align-items:center;justify-content:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}"
        ".detail-count{flex:0 0 calc(var(--cell)*2 - var(--gap));color:#80d6a3;font-weight:900}"
        ".detail-core-ability{flex:1 1 0;min-width:0;color:var(--orange)}"
        ".detail-waha{flex:0 0 calc(var(--cell)*3 - var(--gap));width:auto!important;text-decoration:none}"
    )
    if doc.count(css_anchor) != 1:
        raise SystemExit(f'{label} detail CSS anchor: expected 1 match, found {doc.count(css_anchor)}')
    doc = doc.replace(css_anchor, css_add, 1)

    old_hidden = ".detail-waha,.detail-deep-strike,.weapon-header,.weapon-row-1,.weapon-tags-1,.weapon-row-2,.weapon-tags-2,.weapon-row-3,.weapon-tags-3,.weapon-row-4,.weapon-tags-4,.weapon-row-5,.weapon-tags-5{display:none}"
    new_hidden = ".detail-box-row,.weapon-header,.weapon-row-1,.weapon-tags-1,.weapon-row-2,.weapon-tags-2,.weapon-row-3,.weapon-tags-3,.weapon-row-4,.weapon-tags-4,.weapon-row-5,.weapon-tags-5{display:none}"
    if doc.count(old_hidden) != 1:
        raise SystemExit(f'{label} hidden detail selector: expected 1 match, found {doc.count(old_hidden)}')
    doc = doc.replace(old_hidden, new_hidden, 1)

    old_mock = """function addExpandedUnitMock(f){
  const w=document.createElement('a');w.className='button-standard detail-waha';w.textContent='Waha';w.href='#';w.onclick=e=>{e.preventDefault();e.stopPropagation();const url=String(w.getAttribute('href')||'').trim();if(!url||url==='#')return;try{if(parent&&typeof parent.openAlternateViewWaha==='function')parent.openAlternateViewWaha(url)}catch(_){}};f.appendChild(w);"""
    new_mock = """function addExpandedUnitMock(f){
  const boxRow=document.createElement('div');boxRow.className='detail-box-row';
  const detailCount=document.createElement('div');detailCount.className='detail-box detail-count';detailCount.textContent='';boxRow.appendChild(detailCount);
  const w=document.createElement('a');w.className='detail-box detail-waha';w.textContent='Waha';w.href='#';w.onclick=e=>{e.preventDefault();e.stopPropagation();const url=String(w.getAttribute('href')||'').trim();if(!url||url==='#')return;try{if(parent&&typeof parent.openAlternateViewWaha==='function')parent.openAlternateViewWaha(url)}catch(_){}};boxRow.appendChild(w);f.appendChild(boxRow);"""
    if doc.count(old_mock) != 1:
        raise SystemExit(f'{label} expanded detail row constructor: expected 1 match, found {doc.count(old_mock)}')
    doc = doc.replace(old_mock, new_mock, 1)

    unit_data_marker = "let unitDataByIndex=[null,null];"
    unit_data_new = unit_data_marker + f"\nconst HIDE_SINGLETON_COUNT={'true' if hide_singleton else 'false'};"
    if doc.count(unit_data_marker) != 1:
        raise SystemExit(f'{label} unit data marker: expected 1 match, found {doc.count(unit_data_marker)}')
    doc = doc.replace(unit_data_marker, unit_data_new, 1)

    old_exclusion = "if(el.matches('.detail-waha,.detail-core-ability,.weapon-header,.weapon-row,.weapon-tags'))return;"
    new_exclusion = "if(el.matches('.detail-box-row,.weapon-header,.weapon-row,.weapon-tags'))return;"
    if doc.count(old_exclusion) != 1:
        raise SystemExit(f'{label} expanded layout exclusion: expected 1 match, found {doc.count(old_exclusion)}')
    doc = doc.replace(old_exclusion, new_exclusion, 1)

    old_apply = """function applyActiveUnitDetails(){
  const data=activeUnitIndex===null?null:unitDataByIndex[activeUnitIndex];
  const waha=grid.querySelector('.detail-waha');
  if(waha){
    const url=String(data&&data.waha||'').trim();
    waha.dataset.liveAvailable=url?'true':'false';
    waha.href=url||'#';
  }
  grid.querySelectorAll('.detail-core-ability').forEach(el=>el.remove());
  if(data){
    const coreAbilities=Array.isArray(data.coreAbilities)?data.coreAbilities:[];
    coreAbilities.slice(0,4).forEach((ability,index)=>{
      const label=String(ability&&ability.name||'').trim();
      if(!label)return;
      const tag=document.createElement('div');
      tag.className='detail-deep-strike unit-keyword detail-core-ability';
      tag.textContent=label.toUpperCase();
      tag.style.gridColumn=String(4+(index*3))+'/span 3';
      grid.appendChild(tag);
    });
  }
  const weapons=data&&Array.isArray(data.weapons)?data.weapons:[];"""
    new_apply = """function applyActiveUnitDetails(){
  const data=activeUnitIndex===null?null:unitDataByIndex[activeUnitIndex];
  const detailRow=grid.querySelector('.detail-box-row');
  const detailCount=detailRow&&detailRow.querySelector('.detail-count');
  if(detailCount){
    const countValue=Math.max(1,Number(data&&data.count)||1);
    const countOptionCount=Math.max(1,Number(data&&data.countOptionCount)||1);
    const showCount=Boolean(data)&&!(HIDE_SINGLETON_COUNT&&countValue===1&&countOptionCount===1);
    detailCount.textContent='x'+String(countValue);
    detailCount.style.display=showCount?'inline-flex':'none';
  }
  const waha=detailRow&&detailRow.querySelector('.detail-waha');
  if(waha){
    const url=String(data&&data.waha||'').trim();
    waha.dataset.liveAvailable=url?'true':'false';
    waha.href=url||'#';
    waha.style.display=url?'inline-flex':'none';
  }
  grid.querySelectorAll('.detail-core-ability').forEach(el=>el.remove());
  if(data&&detailRow){
    const coreAbilities=Array.isArray(data.coreAbilities)?data.coreAbilities:[];
    coreAbilities.slice(0,4).forEach(ability=>{
      const label=String(ability&&ability.name||'').trim();
      if(!label)return;
      const tag=document.createElement('div');
      tag.className='detail-box unit-keyword detail-core-ability';
      tag.textContent=label.toUpperCase();
      detailRow.insertBefore(tag,waha||null);
    });
  }
  const weapons=data&&Array.isArray(data.weapons)?data.weapons:[];"""
    if doc.count(old_apply) != 1:
        raise SystemExit(f'{label} active detail renderer: expected 1 match, found {doc.count(old_apply)}')
    doc = doc.replace(old_apply, new_apply, 1)

    old_mute = "grid.querySelectorAll('.detail-waha,.detail-core-ability').forEach(el=>{el.classList.remove('keyword-muted');el.classList.toggle('detail-row-muted',hasSelection)});"
    new_mute = "grid.querySelectorAll('.detail-box-row .detail-box').forEach(el=>{el.classList.remove('keyword-muted');el.classList.toggle('detail-row-muted',hasSelection)});"
    if doc.count(old_mute) != 1:
        raise SystemExit(f'{label} detail mute selector: expected 1 match, found {doc.count(old_mute)}')
    doc = doc.replace(old_mute, new_mute, 1)

    old_visibility = """  const waha=grid.querySelector('.detail-waha');
  if(waha){waha.style.gridRow=String(detailStartRow);waha.style.display=activeUnitIndex!==null&&waha.dataset.liveAvailable==='true'?'inline-flex':'none'}
  grid.querySelectorAll('.detail-core-ability').forEach(el=>{
    el.style.gridRow=String(detailStartRow);
    el.style.display=activeUnitIndex!==null?'flex':'none';
  });
  syncWeaponLayout();"""
    new_visibility = """  const detailRow=grid.querySelector('.detail-box-row');
  if(detailRow){detailRow.style.gridRow=String(detailStartRow);detailRow.style.display=activeUnitIndex!==null?'flex':'none'}
  syncWeaponLayout();"""
    if doc.count(old_visibility) != 1:
        raise SystemExit(f'{label} detail visibility block: expected 1 match, found {doc.count(old_visibility)}')
    doc = doc.replace(old_visibility, new_visibility, 1)

    old_count = """    let count=row.querySelector('.unit-count-grid');
    if(!count){count=document.createElement('div');count.className='unit-count-grid';row.appendChild(count)}
    count.textContent='x'+String(data.count??1);"""
    new_count = """    const count=row.querySelector('.unit-count-grid');
    if(count)count.remove();"""
    if doc.count(old_count) != 1:
        raise SystemExit(f'{label} Unit-row count renderer: expected 1 match, found {doc.count(old_count)}')
    doc = doc.replace(old_count, new_count, 1)

    return doc


view_np = patch_detail_doc(view_np, True, 'New View')
edit_np = patch_detail_doc(edit_np, False, 'New Edit')

# New Edit must know whether x1 is the only current canonical point option so
# New View can hide only that specific singleton case while New Edit still shows it.
old_count_contract = '        count: entry && unit ? getRosterEntryModelCount(entry, unit) : 1,\n'
new_count_contract = old_count_contract + '        countOptionCount: entry && unit ? getRosterEntryPointOptions(entry, unit).length : 1,\n'
if text.count(old_count_contract) != 1:
    raise SystemExit(f'Unit count-option contract: expected 1 match, found {text.count(old_count_contract)}')
text = text.replace(old_count_contract, new_count_contract, 1)

# Write both embedded documents back.
text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]
em = edit_pat.search(text)
if not em:
    raise SystemExit('New Edit iframe missing after New View writeback')
text = text[:em.start(2)] + html.escape(edit_np, quote=True) + text[em.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.82
    Scope: Standardize the Unit detail line directly below the Unit name in both New Edit and New View. Quantity is now the first detail box, canonical Unit/core badges follow it, and Waha is always the last detail box. All three use one shared detail-box visual contract for height, border, radius, padding, typography, background, and spacing; only semantic text state differs. Quantity is moved out of the Unit profile row into this detail line. New Edit always shows the staged xN quantity. New View hides x1 only when the current canonical CSV/runtime point-option set contains exactly one option; x5 or any selectable/multi-option quantity remains visible. New Edit stages the new countOptionCount field from the existing Old Edit/model source, and New View continues to consume the complete Unit record only through New Edit.
    Risk areas: New Edit/New View Unit detail-row presentation and the staged Unit count-option metadata only. Title linkage, profile stats, Weapons, Weapon Tags/scope, Waha routing action, Old Edit behavior, Cards, persistence, CSV contents, and Probable are unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.81\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.77\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

# Acceptance checks.
vm = view_pat.search(text)
em = edit_pat.search(text)
if not vm or not em:
    raise SystemExit('final New View/New Edit iframe verification failed')
final_view = html.unescape(vm.group(2))
final_edit = html.unescape(em.group(2))

for doc, label, hide_value in [(final_view, 'New View', 'true'), (final_edit, 'New Edit', 'false')]:
    for required in [
        f'const HIDE_SINGLETON_COUNT={hide_value};',
        "boxRow.className='detail-box-row'",
        "detailCount.className='detail-box detail-count'",
        "w.className='detail-box detail-waha'",
        "tag.className='detail-box unit-keyword detail-core-ability'",
        "detailRow.insertBefore(tag,waha||null);",
        "detailCount.textContent='x'+String(countValue);",
        "const count=row.querySelector('.unit-count-grid');",
        "if(count)count.remove();",
        ".detail-box{height:var(--std);padding:0 8px;border:1px solid var(--btnborder);border-radius:var(--radius);background:var(--btn);",
    ]:
        if required not in doc:
            raise SystemExit(f'{label} detail-row acceptance failed: {required}')
    if "w.className='button-standard detail-waha'" in doc:
        raise SystemExit(f'{label} Waha still uses separate button-standard styling')
    if "tag.className='detail-deep-strike unit-keyword detail-core-ability'" in doc:
        raise SystemExit(f'{label} core ability still uses old separate badge styling')

if "HIDE_SINGLETON_COUNT&&countValue===1&&countOptionCount===1" not in final_view:
    raise SystemExit('New View singleton x1 rule missing')
if 'parent.getNewEditUnitData(index)' not in final_view:
    raise SystemExit('New View Unit data no longer sourced from New Edit')
if 'parent.getAlternateViewUnitData(index)' in final_view:
    raise SystemExit('New View regained direct Old Edit/model Unit dependency')
if 'parent.getAlternateViewUnitData(index)' not in final_edit:
    raise SystemExit('New Edit temporary Old Edit/model upstream feed missing')
if 'countOptionCount: entry && unit ? getRosterEntryPointOptions(entry, unit).length : 1,' not in text:
    raise SystemExit('countOptionCount contract missing')

for required in [
    '<title>WH40k 11th V31.82</title>',
    'const APP_VERSION = "31.82";',
    "version: 'V31.82',",
    'CHANGE NOTE - WH40k_11th_V31.82',
]:
    if required not in text:
        raise SystemExit('version acceptance check failed: ' + required)

out.write_text(text, encoding='utf-8')
print('Built V31.82: standardized Unit detail boxes, quantity first, Waha last, singleton x1 hidden only in New View')
