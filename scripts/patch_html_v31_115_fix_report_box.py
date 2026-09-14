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


# Sequential release metadata, rebased on current V31.114.
once('<title>WH40k 11th V31.114</title>', '<title>WH40k 11th V31.115</title>', 'title')
once('The current baseline is WH40k_11th_V31.114;', 'The current baseline is WH40k_11th_V31.115;', 'baseline')
once('const APP_VERSION = "31.114";', 'const APP_VERSION = "31.115";', 'APP_VERSION')
once("version: 'V31.114',", "version: 'V31.115',", 'quality version')

# Store FIX Report rows inside the already roster-persisted Spreadsheet Edits object.
# This gives the report the same Save/reload/clone/export/import lifecycle without
# mixing it into actual spreadsheet patch rows.
once(
    'function createEmptySpreadsheetEdits() {\n      return { detachmentEnhancements: {}, detachmentRules: {}, detachmentStratagems: {}, units: {}, abilities: {}, weapons: {} };\n    }',
    'function createEmptySpreadsheetEdits() {\n      return { detachmentEnhancements: {}, detachmentRules: {}, detachmentStratagems: {}, units: {}, abilities: {}, weapons: {}, fixReports: [] };\n    }',
    'empty spreadsheet edits shape'
)

normalize_marker = '    function normalizeRosterSpreadsheetEdits(value) {'
if text.count(normalize_marker) != 1:
    raise SystemExit(f'normalize spreadsheet edits marker: expected 1 match, found {text.count(normalize_marker)}')
fix_normalizers = r'''    function normalizeFixReportItems(value) {
      const source = Array.isArray(value) ? value : [];
      const seen = new Set();
      const result = [];
      source.forEach(raw => {
        if (!raw || typeof raw !== "object") return;
        const unit = String(raw.unit || "Unit").trim() || "Unit";
        let selected = String(raw.selected || "").trim();
        const section = String(raw.section || "").trim();
        const item = String(raw.item || "").trim();
        const field = String(raw.field || "").trim();
        const valueText = String(raw.value ?? "").trim();
        if (!selected) {
          const parts = [];
          if (section) parts.push(section);
          if (item && item !== unit && item !== section) parts.push(item);
          if (field && field !== item) parts.push(field);
          selected = parts.join(" > ") || "Item";
        }
        const key = [unit, selected, valueText].join("\u001f");
        if (seen.has(key)) return;
        seen.add(key);
        result.push({
          unit,
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
        `Unit: ${item.unit}`,
        `Selected: ${item.selected}`,
        `Current Value: ${item.value}`
      ].join("\n"));
      return `FIX REPORT\n\n${blocks.join("\n\n")}`;
    }

'''
text = text.replace(normalize_marker, fix_normalizers + normalize_marker, 1)

once(
    '        weapons: normalizeGroup(source.weapons, normalizePendingWeaponSpreadsheetEdit)\n      };',
    '        weapons: normalizeGroup(source.weapons, normalizePendingWeaponSpreadsheetEdit),\n        fixReports: normalizeFixReportItems(source.fixReports)\n      };',
    'persist FIX reports in spreadsheet edit normalizer'
)

# V31.113 temporarily repurposed legacy per-Unit Notes for FIX storage. Migrate any
# such existing notes into the new visible report once, then restore normal Notes retirement.
old_strip = r'''    function isFixReportAbilityNote(note) {
      return String(note && note.title || "").trim().toUpperCase() === "FIX";
    }

    function stripAllRosterNotes(roster) {
      if (!roster) return roster;
      roster.rosterNotes = [];
      roster.entries = (Array.isArray(roster.entries) ? roster.entries : []).filter(entry => !isRosterNoteEntry(entry));
      (roster.entries || []).forEach(entry => {
        if (!entry || isSpacerEntry(entry) || isRosterNoteEntry(entry)) return;
        const retainedFixNotes = normalizeRosterUnitAbilityNotes(entry).filter(isFixReportAbilityNote);
        entry.abilityNoteTitle = retainedFixNotes.length ? retainedFixNotes[0].title : "Note";
        entry.abilityNote = retainedFixNotes.length ? retainedFixNotes[0].text : "";
        entry.abilityNotes = retainedFixNotes.map(item => ({ title: item.title, text: item.text }));
        if (entry.abilitySortOrders && typeof entry.abilitySortOrders === "object") {
          Object.keys(entry.abilitySortOrders).forEach(key => {
            if (String(key).startsWith("note:")) delete entry.abilitySortOrders[key];
          });
        }
        if (!entry.abilitySortOrders || typeof entry.abilitySortOrders !== "object") entry.abilitySortOrders = {};
        retainedFixNotes.forEach((item, index) => {
          entry.abilitySortOrders[`note:${index}`] = 1;
        });
      });
      return roster;
    }'''
new_strip = r'''    function stripAllRosterNotes(roster) {
      if (!roster) return roster;
      roster.rosterNotes = [];
      if (!roster.spreadsheetEdits || typeof roster.spreadsheetEdits !== "object") roster.spreadsheetEdits = createEmptySpreadsheetEdits();
      const migratedFixReports = normalizeFixReportItems(roster.spreadsheetEdits.fixReports);
      const seenFixReports = new Set(migratedFixReports.map(item => [item.unit, item.selected, item.value].join("\u001f")));
      roster.entries = (Array.isArray(roster.entries) ? roster.entries : []).filter(entry => !isRosterNoteEntry(entry));
      (roster.entries || []).forEach(entry => {
        if (!entry || isSpacerEntry(entry) || isRosterNoteEntry(entry)) return;
        normalizeRosterUnitAbilityNotes(entry).forEach(note => {
          if (String(note && note.title || "").trim().toUpperCase() !== "FIX") return;
          const lines = String(note.text || "").split(/\r?\n/).map(line => line.trim()).filter(Boolean);
          const unitLine = lines.find(line => /^Unit:\s*/i.test(line));
          const unit = unitLine ? unitLine.replace(/^Unit:\s*/i, "").trim() : "Unit";
          lines.filter(line => !/^Unit:\s*/i.test(line)).forEach(line => {
            const parts = line.split(/\s*>\s*/).map(part => part.trim()).filter(Boolean);
            if (!parts.length) return;
            const value = parts.length > 1 ? parts.pop() : "";
            const selected = parts.join(" > ") || "Item";
            const key = [unit, selected, value].join("\u001f");
            if (seenFixReports.has(key)) return;
            seenFixReports.add(key);
            migratedFixReports.push({ unit, selected, value, createdAt: "" });
          });
        });
        entry.abilityNoteTitle = "Note";
        entry.abilityNote = "";
        entry.abilityNotes = [];
        if (entry.abilitySortOrders && typeof entry.abilitySortOrders === "object") {
          Object.keys(entry.abilitySortOrders).forEach(key => {
            if (String(key).startsWith("note:")) delete entry.abilitySortOrders[key];
          });
        }
      });
      roster.spreadsheetEdits.fixReports = normalizeFixReportItems(migratedFixReports);
      return roster;
    }'''
if text.count(old_strip) != 1:
    raise SystemExit(f'V31.113 FIX-note strip block: expected 1 match, found {text.count(old_strip)}')
text = text.replace(old_strip, new_strip, 1)

# Disable the temporary FIX-note editor again. Notes stay retired; the visible
# report below is now the only reporting surface.
row_sig = '    function renderUnitAbilityNoteEditRow(entry, editKey, note, noteIndex = 0, rowIndex = 0) {'
if text.count(row_sig) != 1:
    raise SystemExit('renderUnitAbilityNoteEditRow signature missing')
row_start = text.index(row_sig)
row_end = text.index('\n\n    function renderUnitAbilityNoteEditRows(', row_start)
row_block = text[row_start:row_end]
if '      return "";' not in row_block[:200]:
    row_block = row_block.replace(row_sig, row_sig + '\n      return "";', 1)
text = text[:row_start] + row_block + text[row_end:]

rows_sig = '    function renderUnitAbilityNoteEditRows(entry, editKey, rowOffset = 0) {'
rows_start = text.index(rows_sig)
rows_end = text.index('\n\n    function refreshAbilityEditRowStriping(', rows_start)
rows_block = text[rows_start:rows_end]
if '      return "";' not in rows_block[:200]:
    rows_block = rows_block.replace(rows_sig, rows_sig + '\n      return "";', 1)
text = text[:rows_start] + rows_block + text[rows_end:]

# Replace the V31.113 per-Unit Note bridge with roster-level visible FIX Report bridges.
bridge_pat = re.compile(r'    window\.saveNewViewFixReportToRoster = function\(report\) \{.*?\n    \};\n\n(?=    function selectAppMode\(mode\) \{)', re.S)
m = bridge_pat.search(text)
if not m:
    raise SystemExit('V31.113 FIX-note parent bridge missing')
new_bridge = r'''    window.getNewViewFixReportItems = function() {
      const roster = getViewEditRoster();
      if (!roster) return [];
      return normalizeFixReportItems(getRosterSpreadsheetEdits(roster).fixReports);
    };

    window.saveNewViewFixReportItems = function(items) {
      const roster = getViewEditRoster();
      if (!roster) return { ok: false, count: 0 };
      const edits = getRosterSpreadsheetEdits(roster);
      const current = normalizeFixReportItems(edits.fixReports);
      const incoming = normalizeFixReportItems((Array.isArray(items) ? items : []).map(item => ({
        unit: String(item && item.unit || "Unit"),
        section: String(item && item.section || ""),
        item: String(item && item.item || ""),
        field: String(item && item.field || ""),
        value: String(item && item.value ?? ""),
        createdAt: new Date().toISOString()
      })));
      edits.fixReports = normalizeFixReportItems(current.concat(incoming));
      roster.spreadsheetEdits = edits;
      viewEditRosterDraftDirty = true;
      rosterWorkingStateDirty = true;
      persistRosterLibrary({ reason: "new-view-fix-report", skipNoteDeleteFinalize: true });
      return { ok: incoming.length > 0, count: edits.fixReports.length };
    };

    window.clearNewViewFixReportItems = function() {
      const roster = getViewEditRoster();
      if (!roster) return false;
      const edits = getRosterSpreadsheetEdits(roster);
      edits.fixReports = [];
      roster.spreadsheetEdits = edits;
      viewEditRosterDraftDirty = true;
      rosterWorkingStateDirty = true;
      persistRosterLibrary({ reason: "new-view-fix-report-clear", skipNoteDeleteFinalize: true });
      return true;
    };

    window.copyNewViewFixReportText = function(button) {
      const roster = getViewEditRoster();
      if (!roster) return false;
      const text = formatFixReportCopyText(getRosterSpreadsheetEdits(roster).fixReports);
      if (!text) return false;
      RosterActions.copyTextToClipboardWithFeedback(text, button, "Copy All");
      return true;
    };

'''
text = text[:m.start()] + new_bridge + text[m.end():]

# Modify the unified New View iframe.
view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing')
view_np = html.unescape(vm.group(2))

# Spreadsheet-Edits-inspired report box, but expressed using New View's existing
# 16-column grid, colors, Roboto typography, borders, and standard buttons.
style_marker = '</style>'
fix_css = r'''
.new-view-fix-report-box{grid-column:1/span 16;z-index:4;display:none;align-self:stretch;border:1px solid var(--border);border-radius:var(--radius);background:var(--card);overflow:hidden;color:var(--text);font-family:Roboto,Arial,sans-serif}
.new-view-fix-report-title{height:var(--cell);display:flex;align-items:center;padding:0 8px;border-bottom:1px solid var(--border);font:900 var(--body)/1 Roboto,Arial,sans-serif}
.new-view-fix-report-count{margin-left:auto;color:var(--muted);font:700 var(--meta)/1 Roboto,Arial,sans-serif}
.new-view-fix-report-list{display:block}
.new-view-fix-report-item{min-height:calc(var(--cell)*2);padding:5px 8px;border-bottom:1px solid var(--border);display:flex;flex-direction:column;justify-content:center;gap:3px;overflow:hidden}
.new-view-fix-report-unit{color:var(--text);font:900 var(--body)/1 Roboto,Arial,sans-serif;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.new-view-fix-report-detail{color:var(--secondary);font:700 var(--meta)/1.2 Roboto,Arial,sans-serif;white-space:normal;overflow-wrap:anywhere}
.new-view-fix-report-value{color:var(--orange)}
.new-view-fix-report-actions{height:var(--cell);display:grid;grid-template-columns:repeat(3,1fr);gap:var(--gap);align-items:center;padding:1px 0}
.new-view-fix-report-actions .button-standard{width:100%;height:var(--std);padding:0 4px}
'''
if view_np.count(style_marker) < 1:
    raise SystemExit('New View style marker missing')
view_np = view_np.replace(style_marker, fix_css + style_marker, 1)

# Replace isolated/local report storage with the visible roster-level collection.
# Leave selection mechanics intact; only the save/read destination changes.
local_storage_pat = re.compile(r"const NEW_VIEW_REPORT_STORAGE_KEY='wh40k:new-view-fix-reports:v1';.*?(?=function newViewReportText\(el\)\{)", re.S)
lm = local_storage_pat.search(view_np)
if lm:
    view_np = view_np[:lm.start()] + "let newViewReportMode=false;\nconst newViewReportSelections=new Map();\nconst NEW_VIEW_STAT_FIELDS=['M','T','SV','W','LD','OC'];\nconst NEW_VIEW_WEAPON_FIELDS=['Range','Attacks','Skill','Strength','AP','Damage'];\n\n" + view_np[lm.end():]

# Remove obsolete read/write localStorage helpers and old public getters if present.
view_np = re.sub(r"function readNewViewFixReports\(\)\{.*?\n\}\nfunction writeNewViewFixReports\(reports\)\{.*?\n\}\n", "", view_np, count=1, flags=re.S)
view_np = re.sub(r"window\.getNewViewFixReports=.*?window\.getNewViewLatestFixReport=function\(\)\{.*?\n\};\n\n", "", view_np, count=1, flags=re.S)

# Add report rendering/copy/clear helpers before the existing button sync helper.
helper_marker = 'function syncNewViewReportButtons(){'
if view_np.count(helper_marker) != 1:
    raise SystemExit('New View report sync marker missing')
report_box_helpers = r'''function readNewViewFixReportItems(){
  try{
    if(parent&&typeof parent.getNewViewFixReportItems==='function'){
      const items=parent.getNewViewFixReportItems();
      return Array.isArray(items)?items:[];
    }
  }catch(_){}
  return [];
}
function newViewFixReportRows(){return readNewViewFixReportItems()}
function newViewFixReportGridRows(count){return count?Math.max(4,2+(Math.max(0,count)*2)):0}
function formatNewViewFixReportVisibleValue(value){return String(value??'').trim()}
function buildNewViewFixReportBox(){
  const box=document.createElement('section');
  box.className='new-view-fix-report-box';
  box.setAttribute('aria-label','Fix Report');
  return box;
}
function renderNewViewFixReportBox(){
  const box=grid.querySelector('.new-view-fix-report-box');
  if(!box)return 0;
  const items=newViewFixReportRows();
  if(!items.length){box.style.display='none';box.innerHTML='';return 0}
  box.style.display='block';
  const title=document.createElement('div');
  title.className='new-view-fix-report-title';
  title.textContent='Fix Report';
  const count=document.createElement('span');
  count.className='new-view-fix-report-count';
  count.textContent=String(items.length)+' item'+(items.length===1?'':'s');
  title.appendChild(count);
  const list=document.createElement('div');
  list.className='new-view-fix-report-list';
  items.forEach(item=>{
    const row=document.createElement('div');row.className='new-view-fix-report-item';
    const unit=document.createElement('div');unit.className='new-view-fix-report-unit';unit.textContent=String(item&&item.unit||'Unit');
    const detail=document.createElement('div');detail.className='new-view-fix-report-detail';
    const selected=String(item&&item.selected||'Item');
    const value=formatNewViewFixReportVisibleValue(item&&item.value);
    detail.append(document.createTextNode(selected+' → '));
    const valueSpan=document.createElement('span');valueSpan.className='new-view-fix-report-value';valueSpan.textContent=value;detail.appendChild(valueSpan);
    row.append(unit,detail);list.appendChild(row);
  });
  const actions=document.createElement('div');actions.className='new-view-fix-report-actions';
  const done=document.createElement('button');done.type='button';done.className='button-standard';done.textContent='Done';
  const reset=document.createElement('button');reset.type='button';reset.className='button-standard';reset.textContent='Reset';
  const copy=document.createElement('button');copy.type='button';copy.className='button-standard active-green';copy.textContent='Copy All';
  const clear=()=>{
    try{if(parent&&typeof parent.clearNewViewFixReportItems==='function')parent.clearNewViewFixReportItems()}catch(_){}
    renderNewViewFixReportBox();
    layoutNewViewFixReportAndVersion();
  };
  done.onclick=e=>{e.preventDefault();e.stopPropagation();clear()};
  reset.onclick=e=>{e.preventDefault();e.stopPropagation();clear()};
  copy.onclick=e=>{e.preventDefault();e.stopPropagation();try{if(parent&&typeof parent.copyNewViewFixReportText==='function')parent.copyNewViewFixReportText(copy)}catch(_){}};
  actions.append(done,reset,copy);
  box.replaceChildren(title,list,actions);
  return newViewFixReportGridRows(items.length);
}
function layoutNewViewFixReportAndVersion(){
  const baseVersionRow=getNewViewVersionRow();
  const reportBox=grid.querySelector('.new-view-fix-report-box');
  const reportRows=renderNewViewFixReportBox();
  if(reportBox&&reportRows)reportBox.style.gridRow=String(baseVersionRow)+'/span '+String(reportRows);
  const versionRow=baseVersionRow+reportRows;
  const rowValue=String(versionRow);
  const version=grid.querySelector('.new-view-version-toggle');
  const update=grid.querySelector('.new-view-update-button');
  const download=grid.querySelector('.new-view-download-button');
  [version,update,download].forEach(control=>{if(control&&control.style.gridRow!==rowValue)control.style.gridRow=rowValue});
  grid.querySelectorAll('.new-view-version-option').forEach((button,index)=>{
    button.style.gridRow=String(versionRow+1+Math.floor(index/5));
    button.style.gridColumn=NEW_VIEW_VERSION_HISTORY_COLUMNS[index%5];
  });
  syncNewViewFrameHeight();
  return versionRow;
}
'''
view_np = view_np.replace(helper_marker, report_box_helpers + helper_marker, 1)

# Save selected items directly to the roster-level report and refresh its visible box.
save_start = view_np.index('function saveNewViewFixReport(){')
save_end = view_np.index('function syncNewViewReportButtons(){', save_start)
old_save_region = view_np[save_start:save_end]
new_save = r'''function saveNewViewFixReport(){
  const items=[...newViewReportSelections.values()].map(item=>Object.assign({},item));
  if(!items.length)return {ok:false,count:newViewFixReportRows().length};
  let result={ok:false,count:newViewFixReportRows().length};
  try{
    if(parent&&typeof parent.saveNewViewFixReportItems==='function')result=parent.saveNewViewFixReportItems(items)||result;
  }catch(_){result={ok:false,count:newViewFixReportRows().length}}
  if(result&&result.ok){
    renderNewViewFixReportBox();
    layoutNewViewFixReportAndVersion();
  }
  return result;
}
'''
# Preserve any helper constants/functions between save and sync by removing only save function body.
save_fn_pat = re.compile(r'function saveNewViewFixReport\(\)\{.*?\n\}\n', re.S)
sm = save_fn_pat.search(old_save_region)
if not sm:
    raise SystemExit('New View saveNewViewFixReport function missing')
old_save_region = old_save_region[:sm.start()] + new_save + old_save_region[sm.end():]
view_np = view_np[:save_start] + old_save_region + view_np[save_end:]

# Insert the visible report box into VIEW only.
view_branch = "  if(p==='view'){\n    addViewHeader(f,p);\n    addNewViewReportButton(f);"
if view_np.count(view_branch) != 1:
    raise SystemExit(f'VIEW render branch: expected 1 match, found {view_np.count(view_branch)}')
view_np = view_np.replace(view_branch, view_branch + "\n    f.appendChild(buildNewViewFixReportBox());", 1)

# Version positioning now includes the FIX Report height. The normal unlocked
# background version-position path remains the same gate/counter, while report
# actions may call the pure DOM layout helper even while Lock is on.
position_pat = re.compile(r'function positionNewViewVersionControls\(\)\{.*?\n\}\n(?=function newViewVersionMutationTouchesLayout)', re.S)
pm = position_pat.search(view_np)
if not pm:
    raise SystemExit('positionNewViewVersionControls function missing')
new_position = '''function positionNewViewVersionControls(){if(newViewProcessingLocked())return 0;newViewBackgroundCounters.versionLayoutPasses++;\n  return layoutNewViewFixReportAndVersion();\n}\n'''
view_np = view_np[:pm.start()] + new_position + view_np[pm.end():]

# Locked VIEW already explicitly permits report selection and the wrench. Also
# permit clicks inside the visible report box so Done/Reset/Copy All work.
locked_marker = "  const reportToggle=target.closest('.new-view-report-toggle');"
if view_np.count(locked_marker) != 1:
    raise SystemExit('locked report toggle marker missing')
locked_insert = "  const reportBoxAction=target.closest('.new-view-fix-report-box button');\n  if(reportBoxAction)return;\n"
view_np = view_np.replace(locked_marker, locked_insert + locked_marker, 1)

# Remove obsolete window getter backed by the deleted localStorage path, if a
# partial legacy fragment remains after earlier cleanup.
view_np = view_np.replace("window.getNewViewFixReports=readNewViewFixReports;\n", "")

# Write modified iframe back.
text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

# Release note. Keep only the five newest V31 detailed entries.
note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.115
    Scope: Replace the hidden V31.113 per-Unit FIX-note destination with a visible roster-level Fix Report in unified New View. The wrench still enters/exits lightweight selection mode at L4; the second tap now appends the exact selected Unit / Section / Item / Field / Current Value into a visible Fix Report box directly above Version. The box reuses the New View 16-column grid, Roboto typography, existing card/border/text/orange/green colors, and standard button geometry, with Done, Reset, and Copy All patterned after Spreadsheet Edits. Copy All produces LLM-ready text headed FIX REPORT with Unit, Selected, and Current Value blocks. Report rows persist inside the roster's existing spreadsheetEdits save object so they survive Save/reload/clone/export/import without becoming actual spreadsheet edits. Any FIX notes created by V31.113 are migrated once into the report and legacy Notes return to retired/hidden behavior. No CSV is modified.
    Risk areas: New View report display/Version positioning, FIX report persistence inside spreadsheetEdits, Copy All/Done/Reset actions, and one-time V31.113 FIX-note migration. V31.114 Boyz sub-unit presentation, Lock/filter/Grid controls, unified Edit, Spreadsheet Edits proper, Version/Update/Download behavior, Cards, CSV data, Waha routing, and Probable remain unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.114\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

notes = list(re.finditer(r'\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n', text, re.S))
for match in reversed(notes[5:]):
    text = text[:match.start()] + text[match.end():]

# Acceptance checks.
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing after writeback')
final_view = html.unescape(vm.group(2))

required_view = [
    '.new-view-fix-report-box{grid-column:1/span 16;',
    "title.textContent='Fix Report';",
    "done.textContent='Done';",
    "reset.textContent='Reset';",
    "copy.textContent='Copy All';",
    "parent.saveNewViewFixReportItems(items)",
    "parent.copyNewViewFixReportText(copy)",
    "parent.clearNewViewFixReportItems",
    'function layoutNewViewFixReportAndVersion()',
    'return layoutNewViewFixReportAndVersion();',
    "f.appendChild(buildNewViewFixReportBox());",
    "const reportBoxAction=target.closest('.new-view-fix-report-box button');",
]
for value in required_view:
    if value not in final_view:
        raise SystemExit('V31.115 New View acceptance failed: ' + value)

for forbidden in [
    "wh40k:new-view-fix-reports:v1",
    "parent.saveNewViewFixReportToRoster(report)",
]:
    if forbidden in final_view:
        raise SystemExit('V31.115 obsolete report path remains: ' + forbidden)

required_outer = [
    '<title>WH40k 11th V31.115</title>',
    'The current baseline is WH40k_11th_V31.115;',
    'const APP_VERSION = "31.115";',
    "version: 'V31.115',",
    'fixReports: []',
    'fixReports: normalizeFixReportItems(source.fixReports)',
    'window.getNewViewFixReportItems = function()',
    'window.saveNewViewFixReportItems = function(items)',
    'window.clearNewViewFixReportItems = function()',
    'window.copyNewViewFixReportText = function(button)',
    'CHANGE NOTE - WH40k_11th_V31.115',
]
for value in required_outer:
    if value not in text:
        raise SystemExit('V31.115 outer acceptance failed: ' + value)

path.write_text(text, encoding='utf-8')
print('Built V31.115: visible roster-level FIX Report above Version with Copy All')
