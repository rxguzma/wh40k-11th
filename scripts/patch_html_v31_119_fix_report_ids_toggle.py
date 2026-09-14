from pathlib import Path
import html
import re
import subprocess
import tempfile

path = Path('WH40k_11th.html')
text = path.read_text(encoding='utf-8')


def once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


# Sequential release metadata, rebased on current V31.118.
once('<title>WH40k 11th V31.118</title>', '<title>WH40k 11th V31.119</title>', 'title')
once('The current baseline is WH40k_11th_V31.118;', 'The current baseline is WH40k_11th_V31.119;', 'baseline')
once('const APP_VERSION = "31.118";', 'const APP_VERSION = "31.119";', 'APP_VERSION')
once("version: 'V31.118',", "version: 'V31.119',", 'quality version')

# FIX Report persistence: retain canonical Unit_ID / Weapon_ID and construct the
# LLM-facing Selected path from structured fields instead of display labels.
normalize_start = text.index('    function normalizeFixReportItems(value) {')
normalize_end = text.index('    function normalizeRosterSpreadsheetEdits(value) {', normalize_start)
text = text[:normalize_start] + r'''    function normalizeFixReportItems(value) {
      const source = Array.isArray(value) ? value : [];
      const seen = new Set();
      const result = [];
      source.forEach(raw => {
        if (!raw || typeof raw !== "object") return;
        const unit = String(raw.unit || "Unit").trim() || "Unit";
        const unitId = String(raw.unitId || "").trim();
        const section = String(raw.section || "").trim();
        const item = String(raw.item || "").trim();
        const field = String(raw.field || "").trim();
        const weaponId = String(raw.weaponId || "").trim();
        const valueText = String(raw.value ?? "").trim();
        let selected = String(raw.selected || "").trim();
        if (section || item || field || weaponId) {
          const parts = [];
          if (section) parts.push(section);
          const selectedItem = section.toUpperCase() === "WEAPON" && weaponId ? weaponId : item;
          if (selectedItem && selectedItem !== unit && selectedItem !== section) parts.push(selectedItem);
          if (field && field !== selectedItem) parts.push(field);
          if (parts.length) selected = parts.join(" > ");
        }
        if (!selected) selected = "Item";
        const key = [unitId || unit, selected, valueText].join("\u001f");
        if (seen.has(key)) return;
        seen.add(key);
        result.push({
          unit,
          unitId,
          section,
          item,
          field,
          weaponId,
          selected,
          value: valueText,
          createdAt: String(raw.createdAt || "")
        });
      });
      return result.slice(0, 200);
    }

    function formatFixReportCopyText(items) {
      const rows = normalizeFixReportItems(items);
      if (!rows.length) return "";
      const blocks = rows.map(item => [
        `Unit: ${item.unitId || item.unit}`,
        `Selected: ${item.selected}`,
        `Current Value: ${item.value}`
      ].join("\n"));
      return `FIX REPORT: Check the details called out below vs Waha and suggest changes.\n\n${blocks.join("\n\n")}`;
    }

''' + text[normalize_end:]

# Preserve canonical IDs when New View sends captured report items to roster storage.
save_bridge_start = text.index('    window.saveNewViewFixReportItems = function(items) {')
save_bridge_end = text.index('\n    };', save_bridge_start) + len('\n    };')
save_bridge = text[save_bridge_start:save_bridge_end]
old_map = '''      const incoming = normalizeFixReportItems((Array.isArray(items) ? items : []).map(item => ({
        unit: String(item && item.unit || "Unit"),
        section: String(item && item.section || ""),
        item: String(item && item.item || ""),
        field: String(item && item.field || ""),
        value: String((item && item.value) ?? ""),
        createdAt: new Date().toISOString()
      })));'''
new_map = '''      const incoming = normalizeFixReportItems((Array.isArray(items) ? items : []).map(item => ({
        unit: String(item && item.unit || "Unit"),
        unitId: String(item && item.unitId || ""),
        section: String(item && item.section || ""),
        item: String(item && item.item || ""),
        field: String(item && item.field || ""),
        weaponId: String(item && item.weaponId || ""),
        value: String((item && item.value) ?? ""),
        createdAt: new Date().toISOString()
      })));'''
if save_bridge.count(old_map) != 1:
    raise SystemExit('FIX report parent save mapping anchor missing')
save_bridge = save_bridge.replace(old_map, new_map, 1)
text = text[:save_bridge_start] + save_bridge + text[save_bridge_end:]

# Modify the unified New View iframe.
view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing')
view_np = html.unescape(vm.group(2))

# Unit context carries the canonical Unit_ID already present in New View roster data.
old_context = "  return {index:Number.isFinite(index)?index:null,name:name||'Unit',entryId:String(data&&data.entryId||'').trim()};"
new_context = "  return {index:Number.isFinite(index)?index:null,name:name||'Unit',entryId:String(data&&data.entryId||'').trim(),unitId:String(data&&data.unitId||'').trim()};"
if view_np.count(old_context) != 1:
    raise SystemExit(f'New View Unit context anchor: expected 1 match, found {view_np.count(old_context)}')
view_np = view_np.replace(old_context, new_context, 1)

# Resolve canonical Weapon_ID from the rendered Weapon row. Boyz cloned rows expose
# data-weapon-id directly; standard rows resolve by their stable weapon-row-N slot.
weapon_helper_marker = 'function formatNewViewFixReportItem(item){'
if view_np.count(weapon_helper_marker) != 1:
    raise SystemExit('New View report format helper marker missing')
weapon_helper = r'''function newViewReportWeaponId(el,unit){
  if(!el||!unit)return '';
  const explicit=el.closest('[data-weapon-id]');
  if(explicit&&explicit.dataset&&explicit.dataset.weaponId)return String(explicit.dataset.weaponId||'').trim();
  const node=el.closest('.weapon-row,.weapon-tags,[class*="weapon-row-"],[class*="weapon-tags-"]');
  if(!node)return '';
  let weaponIndex=-1;
  [...node.classList].some(className=>{
    const match=String(className||'').match(/^weapon-(?:row|tags)-(\d+)$/);
    if(!match)return false;
    weaponIndex=Math.max(0,Number(match[1])-1);
    return true;
  });
  if(weaponIndex<0||unit.index===null)return '';
  const data=unitDataByIndex[unit.index];
  const weapons=Array.isArray(data&&data.weapons)?data.weapons:[];
  return String(weapons[weaponIndex]&&weapons[weaponIndex].weaponId||'').trim();
}
'''
view_np = view_np.replace(weapon_helper_marker, weapon_helper + weapon_helper_marker, 1)

old_record = '''  const record={
    unitIndex:unit.index,
    entryId:unit.entryId,
    unit:unit.name,
    section,
    item:item||value,
    field,
    value
  };'''
new_record = '''  const record={
    unitIndex:unit.index,
    entryId:unit.entryId,
    unit:unit.name,
    unitId:unit.unitId,
    section,
    item:item||value,
    field,
    weaponId:section==='Weapon'?newViewReportWeaponId(el,unit):'',
    value
  };'''
if view_np.count(old_record) != 1:
    raise SystemExit(f'New View report record anchor: expected 1 match, found {view_np.count(old_record)}')
view_np = view_np.replace(old_record, new_record, 1)

# Restyle Fix Report header to mirror the Version row: 8 columns of label/count,
# then Done and Copy All as two 4-column actions on the right.
css_replacements = [
    (r'\.new-view-fix-report-title\{[^}]*\}', '.new-view-fix-report-title{height:var(--cell);display:grid;grid-template-columns:repeat(16,var(--cell));align-items:center;padding:0;font:900 var(--body)/1 Roboto,Arial,sans-serif;cursor:pointer}'),
    (r'\.new-view-fix-report-count\{[^}]*\}', '.new-view-fix-report-count{color:var(--muted);font:700 var(--meta)/1 Roboto,Arial,sans-serif;white-space:nowrap}'),
    (r'\.new-view-fix-report-actions\{[^}]*\}', '.new-view-fix-report-actions{grid-column:9/span 8;height:var(--cell);display:grid;grid-template-columns:repeat(2,1fr);align-items:center}'),
    (r'\.new-view-fix-report-actions \.button-standard\{[^}]*\}', '.new-view-fix-report-actions .button-standard{width:calc(100% - var(--gap));height:var(--std);padding:0 4px;justify-self:center}')
]
for pattern, replacement in css_replacements:
    view_np, n = re.subn(pattern, replacement, view_np, count=1)
    if n != 1:
        raise SystemExit('Fix Report CSS anchor missing: ' + pattern)
css_anchor = '.new-view-fix-report-title{height:var(--cell);display:grid;grid-template-columns:repeat(16,var(--cell));align-items:center;padding:0;font:900 var(--body)/1 Roboto,Arial,sans-serif;cursor:pointer}'
view_np = view_np.replace(css_anchor, css_anchor + '\n.new-view-fix-report-heading{grid-column:1/span 8;min-width:0;display:flex;align-items:center;gap:6px;padding:0 8px;white-space:nowrap;overflow:hidden}\n.new-view-fix-report-box.open .new-view-fix-report-title{border-bottom:1px solid var(--border)}', 1)

# Report starts collapsed. Opening adds detail rows; closed state consumes one grid row.
old_rows_fn = "function newViewFixReportGridRows(count){return count?Math.max(4,2+(Math.max(0,count)*2)):0}"
new_rows_fn = "let newViewFixReportOpen=false;\nfunction newViewFixReportGridRows(count){return count?(newViewFixReportOpen?1+(Math.max(0,count)*2):1):0}"
if view_np.count(old_rows_fn) != 1:
    raise SystemExit(f'Fix Report grid-row helper: expected 1 match, found {view_np.count(old_rows_fn)}')
view_np = view_np.replace(old_rows_fn, new_rows_fn, 1)

# Every New View mount begins with the report toggled closed.
build_sig = "function buildNewViewFixReportBox(){\n  const box=document.createElement('section');"
if view_np.count(build_sig) != 1:
    raise SystemExit('Fix Report build function anchor missing')
view_np = view_np.replace(build_sig, "function buildNewViewFixReportBox(){\n  newViewFixReportOpen=false;\n  const box=document.createElement('section');", 1)

# Replace rendering only; layout function remains the established Version-aware positioning path.
render_pat = re.compile(r"function renderNewViewFixReportBox\(\)\{.*?\n\}\n(?=function layoutNewViewFixReportAndVersion\(\)\{)", re.S)
rm = render_pat.search(view_np)
if not rm:
    raise SystemExit('Fix Report render function missing')
new_render = r'''function renderNewViewFixReportBox(){
  const box=grid.querySelector('.new-view-fix-report-box');
  if(!box)return 0;
  const items=newViewFixReportRows();
  if(!items.length){
    newViewFixReportOpen=false;
    box.classList.remove('open');
    box.style.display='none';
    box.innerHTML='';
    return 0;
  }
  box.style.display='block';
  box.classList.toggle('open',newViewFixReportOpen);

  const title=document.createElement('div');
  title.className='new-view-fix-report-title';
  title.setAttribute('aria-expanded',newViewFixReportOpen?'true':'false');
  title.tabIndex=0;

  const heading=document.createElement('div');
  heading.className='new-view-fix-report-heading';
  const label=document.createElement('span');
  label.textContent='Fix Report';
  const count=document.createElement('span');
  count.className='new-view-fix-report-count';
  count.textContent=String(items.length)+' item'+(items.length===1?'':'s');
  heading.append(label,count);

  const actions=document.createElement('div');
  actions.className='new-view-fix-report-actions';
  const done=document.createElement('button');
  done.type='button';done.className='button-standard';done.textContent='Done';
  const copy=document.createElement('button');
  copy.type='button';copy.className='button-standard active-green';copy.textContent='Copy All';
  done.onclick=e=>{
    e.preventDefault();e.stopPropagation();
    try{if(parent&&typeof parent.clearNewViewFixReportItems==='function')parent.clearNewViewFixReportItems()}catch(_){}
    newViewFixReportOpen=false;
    layoutNewViewFixReportAndVersion();
  };
  copy.onclick=e=>{
    e.preventDefault();e.stopPropagation();
    try{if(parent&&typeof parent.copyNewViewFixReportText==='function')parent.copyNewViewFixReportText(copy)}catch(_){}
  };
  actions.append(done,copy);
  title.append(heading,actions);

  const toggleOpen=()=>{
    newViewFixReportOpen=!newViewFixReportOpen;
    layoutNewViewFixReportAndVersion();
  };
  title.onclick=e=>{if(e.target.closest('button'))return;toggleOpen()};
  title.onkeydown=e=>{
    if(e.target.closest('button'))return;
    if(e.key==='Enter'||e.key===' '){e.preventDefault();toggleOpen()}
  };

  if(!newViewFixReportOpen){
    box.replaceChildren(title);
    return newViewFixReportGridRows(items.length);
  }

  const list=document.createElement('div');
  list.className='new-view-fix-report-list';
  items.forEach(item=>{
    const row=document.createElement('div');
    row.className='new-view-fix-report-item';
    const unit=document.createElement('div');
    unit.className='new-view-fix-report-unit';
    unit.textContent='Unit: '+String(item.unitId||item.unit||'Unit');
    const selected=document.createElement('div');
    selected.className='new-view-fix-report-detail';
    selected.textContent='Selected: '+String(item.selected||'Item');
    const value=document.createElement('div');
    value.className='new-view-fix-report-detail new-view-fix-report-value';
    value.textContent='Current Value: '+formatNewViewFixReportVisibleValue(item.value);
    row.append(unit,selected,value);
    list.appendChild(row);
  });
  box.replaceChildren(title,list);
  return newViewFixReportGridRows(items.length);
}
'''
view_np = view_np[:rm.start()] + new_render + view_np[rm.end():]

# Locked VIEW must permit tapping the whole Fix Report row, not only its buttons.
old_locked = "  const reportBoxAction=target.closest('.new-view-fix-report-box button');\n  if(reportBoxAction)return;"
new_locked = "  const reportBoxAction=target.closest('.new-view-fix-report-box');\n  if(reportBoxAction)return;"
if view_np.count(old_locked) != 1:
    raise SystemExit(f'Locked Fix Report click exception: expected 1 match, found {view_np.count(old_locked)}')
view_np = view_np.replace(old_locked, new_locked, 1)

text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.119
    Scope: Refine unified New View Fix Report only. Newly captured report entries now preserve canonical Unit_ID and Weapon_ID from the rendered roster/Weapon data; Copy All and the visible report use Unit_ID instead of Unit display name and Weapon_ID instead of Weapon display name while keeping Current Value human-readable. Copy All now begins exactly with “FIX REPORT: Check the details called out below vs Waha and suggest changes.” The report surface now mirrors the Version row: it starts collapsed, toggles open by tapping the Fix Report row, and keeps only Done and Copy All as two four-column actions on the right; Reset is removed. Existing grid dimensions, Roboto fonts, colors, borders, Version positioning, and wrench behavior are reused.
    Risk areas: Fix Report capture metadata, Copy All formatting, collapsed/open report layout, and locked-View report-row tapping only. Boyz sub-units, other Units, filters, unified Edit, Version controls, Cards, roster/CSV data, Waha routing, and Probable remain unchanged.
  -->

'''
marker = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.118\n'
if text.count(marker) != 1:
    raise SystemExit('V31.118 change-note insertion marker missing')
text = text.replace(marker, note + marker, 1)

# Keep only the five newest detailed V31 change notes.
notes = list(re.finditer(r'\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n', text, re.S))
for match in reversed(notes[5:]):
    text = text[:match.start()] + text[match.end():]

# Acceptance checks.
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing after writeback')
final_view = html.unescape(vm.group(2))
for expected in [
    '<title>WH40k 11th V31.119</title>',
    'The current baseline is WH40k_11th_V31.119;',
    'const APP_VERSION = "31.119";',
    "version: 'V31.119',",
    'FIX REPORT: Check the details called out below vs Waha and suggest changes.',
    'unitId: String(item && item.unitId || "")',
    'weaponId: String(item && item.weaponId || "")',
    "unitId:String(data&&data.unitId||'').trim()",
    "weaponId:section==='Weapon'?newViewReportWeaponId(el,unit):''",
    "done.textContent='Done'",
    "copy.textContent='Copy All'",
    'let newViewFixReportOpen=false;',
    "box.replaceChildren(title);",
    "const reportBoxAction=target.closest('.new-view-fix-report-box');",
    'CHANGE NOTE - WH40k_11th_V31.119',
]:
    target = final_view if expected in [
        "unitId:String(data&&data.unitId||'').trim()",
        "weaponId:section==='Weapon'?newViewReportWeaponId(el,unit):''",
        "done.textContent='Done'",
        "copy.textContent='Copy All'",
        'let newViewFixReportOpen=false;',
        "box.replaceChildren(title);",
        "const reportBoxAction=target.closest('.new-view-fix-report-box');",
    ] else text
    if expected not in target:
        raise SystemExit('V31.119 acceptance failed: ' + expected)

render_block = final_view[final_view.index('function renderNewViewFixReportBox(){'):final_view.index('function layoutNewViewFixReportAndVersion(){')]
if "reset.textContent='Reset'" in render_block or "textContent='Reset'" in render_block:
    raise SystemExit('V31.119 acceptance failed: Reset remains in Fix Report render path')
if 'item && item.value ??' in text:
    raise SystemExit('V31.119 acceptance failed: invalid && / ?? expression returned')

# Parse-check JavaScript before publishing so a syntax regression cannot produce another unloadable release.
def node_check_scripts(source, label):
    scripts = []
    for match in re.finditer(r'<script([^>]*)>(.*?)</script>', source, re.S | re.I):
        attrs = match.group(1) or ''
        type_match = re.search(r'type=["\']([^"\']+)["\']', attrs, re.I)
        if type_match and type_match.group(1).lower() not in ('text/javascript', 'application/javascript', 'module'):
            continue
        scripts.append(match.group(2))
    if not scripts:
        return
    for index, script in enumerate(scripts):
        with tempfile.NamedTemporaryFile('w', suffix='.mjs' if 'type="module"' in source else '.js', delete=False, encoding='utf-8') as tmp:
            tmp.write(script)
            tmp_path = tmp.name
        result = subprocess.run(['node', '--check', tmp_path], capture_output=True, text=True)
        Path(tmp_path).unlink(missing_ok=True)
        if result.returncode != 0:
            raise SystemExit(f'JavaScript parse check failed for {label} script {index + 1}:\n{result.stderr}')

# Check parent/main scripts and the decoded New View srcdoc scripts separately.
outer_without_srcdoc = view_pat.sub(r'\1\3', text)
node_check_scripts(outer_without_srcdoc, 'outer HTML')
node_check_scripts(final_view, 'New View srcdoc')

path.write_text(text, encoding='utf-8')
print('Built V31.119: FIX Report IDs, prompt intro, collapsed row, Done/Copy All only')
