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

once('<title>WH40k 11th V31.112</title>', '<title>WH40k 11th V31.113</title>', 'title')
once('The current baseline is WH40k_11th_V31.112;', 'The current baseline is WH40k_11th_V31.113;', 'baseline')
once('const APP_VERSION = "31.112";', 'const APP_VERSION = "31.113";', 'APP_VERSION')
once("version: 'V31.112',", "version: 'V31.113',", 'quality version')

strip_marker = '    function stripAllRosterNotes(roster) {'
if text.count(strip_marker) != 1:
    raise SystemExit(f'stripAllRosterNotes marker: expected 1 match, found {text.count(strip_marker)}')
text = text.replace(strip_marker, '''    function isFixReportAbilityNote(note) {
      return String(note && note.title || "").trim().toUpperCase() === "FIX";
    }

''' + strip_marker, 1)

once(
'''        entry.abilityNoteTitle = "Note";
        entry.abilityNote = "";
        entry.abilityNotes = [];''',
'''        const retainedFixNotes = normalizeRosterUnitAbilityNotes(entry).filter(isFixReportAbilityNote);
        entry.abilityNoteTitle = retainedFixNotes.length ? retainedFixNotes[0].title : "Note";
        entry.abilityNote = retainedFixNotes.length ? retainedFixNotes[0].text : "";
        entry.abilityNotes = retainedFixNotes.map(item => ({ title: item.title, text: item.text }));''',
'retain FIX notes'
)

strip_start = text.index(strip_marker)
strip_end = text.find('\n\n    function ', strip_start + len(strip_marker))
if strip_end < 0:
    raise SystemExit('stripAllRosterNotes end marker missing')
strip_block = text[strip_start:strip_end]
cleanup = '''        if (entry.abilitySortOrders && typeof entry.abilitySortOrders === "object") {
          Object.keys(entry.abilitySortOrders).forEach(key => {
            if (String(key).startsWith("note:")) delete entry.abilitySortOrders[key];
          });
        }'''
if strip_block.count(cleanup) != 1:
    raise SystemExit(f'note order cleanup: expected 1 match, found {strip_block.count(cleanup)}')
strip_block = strip_block.replace(cleanup, cleanup + '''
        if (!entry.abilitySortOrders || typeof entry.abilitySortOrders !== "object") entry.abilitySortOrders = {};
        retainedFixNotes.forEach((item, index) => {
          entry.abilitySortOrders[`note:${index}`] = 1;
        });''', 1)
text = text[:strip_start] + strip_block + text[strip_end:]

row_start = text.index('    function renderUnitAbilityNoteEditRow(entry, editKey, note, noteIndex = 0, rowIndex = 0) {')
row_end = text.index('\n\n    function renderUnitAbilityNoteEditRows(', row_start)
row_block = text[row_start:row_end]
if '      return "";\n' not in row_block:
    raise SystemExit('retired Note row early return missing')
row_block = row_block.replace('      return "";\n', '', 1)
old_guard = '      if (!entry || isRosterNoteEntry(entry)) return "";'
if row_block.count(old_guard) != 1:
    raise SystemExit('FIX note guard anchor missing')
row_block = row_block.replace(old_guard, '      if (!entry || isRosterNoteEntry(entry) || !isFixReportAbilityNote(note)) return "";', 1)
title_token = 'data-ability-note-field="abilityNoteTitle" role="textbox" contenteditable="true"'
if row_block.count(title_token) != 1:
    raise SystemExit('FIX note title field anchor missing')
row_block = row_block.replace(title_token, 'data-ability-note-field="abilityNoteTitle" role="textbox" contenteditable="false"', 1)
text = text[:row_start] + row_block + text[row_end:]

rows_start = text.index('    function renderUnitAbilityNoteEditRows(entry, editKey, rowOffset = 0) {')
rows_end = text.index('\n\n    function refreshAbilityEditRowStriping(', rows_start)
text = text[:rows_start] + '''    function renderUnitAbilityNoteEditRows(entry, editKey, rowOffset = 0) {
      if (!entry || isRosterNoteEntry(entry)) return "";
      const notes = getRosterEntryAbilityNotes(entry);
      return notes.map((note, index) => isFixReportAbilityNote(note)
        ? renderUnitAbilityNoteEditRow(entry, editKey, note, index, rowOffset + index)
        : "").join("");
    }''' + text[rows_end:]

parent_marker = '    function selectAppMode(mode) {'
if text.count(parent_marker) != 1:
    raise SystemExit(f'parent bridge marker: expected 1 match, found {text.count(parent_marker)}')
parent_bridge = r'''    window.saveNewViewFixReportToRoster = function(report) {
      const items = report && Array.isArray(report.items) ? report.items : [];
      if (!items.length) return { ok: false, savedNotes: 0 };
      const roster = getViewEditRoster();
      if (!roster || !Array.isArray(roster.entries)) return { ok: false, savedNotes: 0 };

      const byEntryId = new Map();
      items.forEach(item => {
        const entryId = String(item && item.entryId || "").trim();
        if (!entryId) return;
        if (!byEntryId.has(entryId)) byEntryId.set(entryId, []);
        byEntryId.get(entryId).push(item);
      });

      let savedNotes = 0;
      byEntryId.forEach((unitItems, entryId) => {
        const entry = getRosterEntryById(roster, entryId);
        if (!entry || isSpacerEntry(entry) || isRosterNoteEntry(entry)) return;

        const unitName = String(unitItems[0] && unitItems[0].unit || "").trim() || "Unit";
        const lines = unitItems.map(item => {
          const section = String(item && item.section || "View").trim() || "View";
          const itemName = String(item && item.item || "").trim();
          const field = String(item && item.field || "Item").trim() || "Item";
          const value = String(item && item.value || "").trim();
          const parts = [section];
          if (itemName && itemName !== section) parts.push(itemName);
          if (field && field !== itemName) parts.push(field);
          if (value && value !== itemName && value !== field) parts.push(value);
          return parts.join(" > ");
        }).filter(Boolean);
        if (!lines.length) return;

        const currentNotes = normalizeRosterUnitAbilityNotes(entry);
        const nextIndex = currentNotes.length;
        const fixText = [`Unit: ${unitName}`, ...lines].join("\n");
        entry.abilityNotes = currentNotes.concat([{ title: "FIX", text: fixText }]);
        entry.abilityNoteTitle = entry.abilityNotes[0].title;
        entry.abilityNote = entry.abilityNotes[0].text;
        if (!entry.abilitySortOrders || typeof entry.abilitySortOrders !== "object") entry.abilitySortOrders = {};
        entry.abilitySortOrders[`note:${nextIndex}`] = 1;
        synchronizeRosterUnitAbilityCollections(entry);
        savedNotes += 1;
      });

      if (!savedNotes) return { ok: false, savedNotes: 0 };
      viewEditRosterDraftDirty = true;
      rosterWorkingStateDirty = true;
      invalidateRosterModeDomCache("view");
      persistRosterLibrary({ reason: "new-view-fix-report", skipNoteDeleteFinalize: true });
      return { ok: true, savedNotes };
    };

'''
text = text.replace(parent_marker, parent_bridge + parent_marker, 1)

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing')
view_np = html.unescape(vm.group(2))

old_context_return = "  return {index:Number.isFinite(index)?index:null,name:name||'Unit'};"
if view_np.count(old_context_return) != 1:
    raise SystemExit('report Unit context anchor missing')
view_np = view_np.replace(old_context_return, "  return {index:Number.isFinite(index)?index:null,name:name||'Unit',entryId:String(data&&data.entryId||'').trim()};", 1)

old_record = '''  const record={
    unitIndex:unit.index,
    unit:unit.name,
    section,
    item:item||value,
    field,
    value
  };'''
if view_np.count(old_record) != 1:
    raise SystemExit('report record anchor missing')
view_np = view_np.replace(old_record, '''  const record={
    unitIndex:unit.index,
    entryId:unit.entryId,
    unit:unit.name,
    section,
    item:item||value,
    field,
    value
  };''', 1)

save_start = view_np.index('function saveNewViewFixReport(){')
save_end = view_np.index('function syncNewViewReportButtons(){', save_start)
view_np = view_np[:save_start] + r'''function saveNewViewFixReport(){
  const items=[...newViewReportSelections.values()].map(item=>Object.assign({},item));
  if(!items.length)return {ok:false,savedNotes:0};
  const rosterNode=grid.querySelector('.top-roster-name');
  const roster=newViewReportText(rosterNode)||'Roster';
  const createdAt=new Date().toISOString();
  const report={
    id:String(Date.now()),
    type:'fix-report',
    title:'FIX',
    roster,
    createdAt,
    items,
    body:items.map(formatNewViewFixReportItem).join('\n')
  };
  let result={ok:false,savedNotes:0};
  try{
    if(parent&&typeof parent.saveNewViewFixReportToRoster==='function'){
      result=parent.saveNewViewFixReportToRoster(report)||result;
    }
  }catch(_){result={ok:false,savedNotes:0}}
  if(result&&result.ok)window.newViewLastFixReport=report;
  return result;
}
''' + view_np[save_end:]

sync_end = view_np.index('function refreshNewViewReportMarks(){', view_np.index('function syncNewViewReportButtons(){'))
view_np = view_np[:sync_end] + r'''const NEW_VIEW_REPORT_WRENCH_HTML='<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M14.7 6.3a4 4 0 0 0-5.2-5.2l2.2 2.2-2.8 2.8-2.2-2.2a4 4 0 0 0 5.2 5.2L4.3 16.7a2.1 2.1 0 0 0 3 3l7.6-7.6a4 4 0 0 0 5.2-5.2l-2.2 2.2-2.8-2.8 2.2-2.2Z"></path></svg>';
const NEW_VIEW_REPORT_CHECK_HTML='<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M5 12.5l4.2 4.2L19 7"></path></svg>';
let newViewReportSavedTimer=0;
function showNewViewReportSaved(){
  if(newViewReportSavedTimer)clearTimeout(newViewReportSavedTimer);
  grid.querySelectorAll('.new-view-report-toggle').forEach(button=>{
    button.innerHTML=NEW_VIEW_REPORT_CHECK_HTML;
    button.classList.add('active-green');
    button.setAttribute('aria-label','Saved');
    button.setAttribute('title','Saved');
  });
  newViewReportSavedTimer=setTimeout(()=>{
    newViewReportSavedTimer=0;
    grid.querySelectorAll('.new-view-report-toggle').forEach(button=>{button.innerHTML=NEW_VIEW_REPORT_WRENCH_HTML});
    syncNewViewReportButtons();
  },700);
}
''' + view_np[sync_end:]

toggle_start = view_np.index('function toggleNewViewReportMode(){')
toggle_end = view_np.index('function addNewViewReportButton(f){', toggle_start)
view_np = view_np[:toggle_start] + r'''function toggleNewViewReportMode(){
  if(newViewReportMode){
    const result=saveNewViewFixReport();
    newViewReportMode=false;
    newViewReportSelections.clear();
    refreshNewViewReportMarks();
    syncNewViewReportButtons();
    if(result&&result.ok)showNewViewReportSaved();
    return false;
  }
  newViewReportMode=true;
  newViewReportSelections.clear();
  syncNewViewReportButtons();
  requestAnimationFrame(refreshNewViewReportMarks);
  return true;
}
''' + view_np[toggle_end:]

button_start = view_np.index('function addNewViewReportButton(f){')
button_end = view_np.index('function handleNewViewReportSelection(event){', button_start)
button_block = view_np[button_start:button_end]
button_block, n = re.subn(r"  button\.innerHTML='<svg .*?</svg>';", "  button.innerHTML=NEW_VIEW_REPORT_WRENCH_HTML;", button_block, count=1, flags=re.S)
if n != 1:
    raise SystemExit(f'report wrench SVG assignment: expected 1 match, found {n}')
view_np = view_np[:button_start] + button_block + view_np[button_end:]

text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.113
    Scope: Complete the New View wrench/FIX workflow. The second wrench tap no longer silently writes an isolated localStorage report. Selected items now save into the roster itself as one per-Unit FIX note, grouped by the exact Unit entryId and preserving the selected hierarchy down to Section / Item / Field / Current Value. FIX notes survive the existing roster Save/reload, clone, export, and import paths while retired legacy Notes remain stripped. Old Edit's existing per-Unit Note editor is selectively re-enabled only for FIX notes; the FIX title is locked and the note body remains editable through the existing Ability Save flow. After a successful second wrench tap, the L4 wrench briefly shows a green checkmark so the save is visible. No source CSV is modified.
    Risk areas: FIX-report roster persistence, selective FIX-note editing in old Edit, and the New View wrench save confirmation only. V31.112 expanded-Unit row-gap fix, Lock/filter/Grid controls, unified Edit, Version/Update/Download, Cards, CSV data, Waha routing, and Probable remain unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.112\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

notes = list(re.finditer(r'\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n', text, re.S))
for match in reversed(notes[5:]):
    text = text[:match.start()] + text[match.end():]

vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing after writeback')
final_view = html.unescape(vm.group(2))

for value in [
    "entryId:String(data&&data.entryId||'').trim()",
    "entryId:unit.entryId,",
    "parent.saveNewViewFixReportToRoster(report)",
    "title:'FIX',",
    'function showNewViewReportSaved()',
    "button.innerHTML=NEW_VIEW_REPORT_CHECK_HTML;",
    'if(result&&result.ok)showNewViewReportSaved();',
    'button.innerHTML=NEW_VIEW_REPORT_WRENCH_HTML;',
]:
    if value not in final_view:
        raise SystemExit('V31.113 New View acceptance failed: ' + value)

for value in [
    '<title>WH40k 11th V31.113</title>',
    'The current baseline is WH40k_11th_V31.113;',
    'const APP_VERSION = "31.113";',
    "version: 'V31.113',",
    'function isFixReportAbilityNote(note)',
    'normalizeRosterUnitAbilityNotes(entry).filter(isFixReportAbilityNote)',
    'window.saveNewViewFixReportToRoster = function(report)',
    'entry.abilityNotes = currentNotes.concat([{ title: "FIX", text: fixText }]);',
    'persistRosterLibrary({ reason: "new-view-fix-report", skipNoteDeleteFinalize: true });',
    'isRosterNoteEntry(entry) || !isFixReportAbilityNote(note)',
    'contenteditable="false"',
    'CHANGE NOTE - WH40k_11th_V31.113',
]:
    if value not in text:
        raise SystemExit('V31.113 outer acceptance failed: ' + value)

save_block = final_view[final_view.index('function saveNewViewFixReport(){'):final_view.index('function syncNewViewReportButtons(){')]
if "writeNewViewFixReports(reports.slice(0,50));" in save_block:
    raise SystemExit('V31.113 report save still writes isolated localStorage')

path.write_text(text, encoding='utf-8')
print('Built V31.113: wrench saves per-Unit FIX notes with visible confirmation')
