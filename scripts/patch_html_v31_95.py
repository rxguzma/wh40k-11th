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


# Sequential release metadata.
once('<title>WH40k 11th V31.94</title>', '<title>WH40k 11th V31.95</title>', 'title')
once('The current baseline is WH40k_11th_V31.94;', 'The current baseline is WH40k_11th_V31.95;', 'baseline')
once('const APP_VERSION = "31.94";', 'const APP_VERSION = "31.95";', 'APP_VERSION')
once("version: 'V31.94',", "version: 'V31.95',", 'quality version')

# ---------------------------------------------------------------------------
# Existing version engine: expose a read-only UI snapshot to New View. Version
# fetching, retained-version loading, update-to-latest, checkpointing, and host
# mounting all remain owned by the existing parent implementation.
# ---------------------------------------------------------------------------
version_fetch_marker = '    async function fetchGithubVersionHistory() { return getVersionHost().history(); }'
version_state_getter = '''    function getVersionUiState() {
      return {
        current: APP_VERSION,
        busy: Boolean(versionActionBusy),
        entries: versionHistoryEntries.map(entry => ({ version: String(entry && entry.version || "") })).filter(entry => entry.version)
      };
    }

    async function fetchGithubVersionHistory() { return getVersionHost().history(); }'''
once(version_fetch_marker, version_state_getter, 'version UI state bridge')

ui_export_old = '''      toggleVersionHistory,
      refreshGithubVersionHistory,'''
ui_export_new = '''      toggleVersionHistory,
      getVersionUiState,
      refreshGithubVersionHistory,'''
once(ui_export_old, ui_export_new, 'UI version state export')

# ---------------------------------------------------------------------------
# New View: add grid-native Version / Update controls. Row 5 is the deliberate
# gap between the four-row header and the row-6 stat header. The history panel
# is a temporary overlay below row 5 so opening it does not renumber, recalc,
# or otherwise process roster rows.
# ---------------------------------------------------------------------------
view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('New View iframe missing')
view_np = html.unescape(vm.group(2))

css_marker = '.version-bar{display:none!important}'
version_css = r'''.version-bar{display:none!important}
.new-view-version-row{grid-column:1/span 16;grid-row:5;z-index:130;display:grid;grid-template-columns:repeat(16,var(--cell));height:var(--cell);align-items:center;background:var(--bg)}
.new-view-version-toggle{grid-column:1/span 12;justify-self:center;justify-content:space-between}
.new-view-version-current{color:var(--muted)}
.new-view-update-button{grid-column:13/span 4;justify-self:center}
.new-view-version-history{grid-column:1/span 16;grid-row:6/span 2;z-index:130;width:100%;height:calc(var(--cell)*2);padding:1px;display:grid;grid-template-columns:repeat(5,minmax(0,1fr));grid-template-rows:repeat(2,var(--std));gap:var(--gap);background:var(--card);border:1px solid var(--border)}
.new-view-version-history[hidden]{display:none!important}
.new-view-version-option{width:100%;padding:0 2px;font-size:11px}
.new-view-version-option:disabled{opacity:1}'''
if view_np.count(css_marker) != 1:
    raise SystemExit(f'New View version CSS marker: expected 1 match, found {view_np.count(css_marker)}')
view_np = view_np.replace(css_marker, version_css, 1)

header_marker = 'function addViewHeader(f,p)'
version_helpers = r'''let newViewVersionHistoryOpen=false;
function readNewViewVersionState(){
  try{
    if(parent&&parent.UI&&typeof parent.UI.getVersionUiState==='function')return parent.UI.getVersionUiState()||{};
  }catch(_){}
  return {};
}
function renderNewViewVersionHistory(){
  const panel=grid.querySelector('.new-view-version-history');
  if(!panel)return;
  panel.hidden=!newViewVersionHistoryOpen;
  panel.replaceChildren();
  if(!newViewVersionHistoryOpen)return;
  const state=readNewViewVersionState();
  const current=String(state.current||'');
  const entries=Array.isArray(state.entries)?state.entries.slice(0,10):[];
  entries.forEach(entry=>{
    const version=String(entry&&entry.version||'');
    if(!version)return;
    const b=document.createElement('button');
    b.type='button';
    b.className='button-standard new-view-version-option'+(version===current?' active-green':'');
    b.textContent='v'+version;
    b.disabled=version===current||Boolean(state.busy);
    b.onclick=event=>{event.stopPropagation();if(b.disabled)return;try{parent.UI.loadGithubVersion(version)}catch(_){}};
    panel.appendChild(b);
  });
}
async function toggleNewViewVersionHistory(){
  newViewVersionHistoryOpen=!newViewVersionHistoryOpen;
  renderNewViewVersionHistory();
  if(!newViewVersionHistoryOpen)return;
  try{
    if(parent&&parent.UI&&typeof parent.UI.refreshGithubVersionHistory==='function')await parent.UI.refreshGithubVersionHistory();
  }catch(_){}
  renderNewViewVersionHistory();
}
function addNewViewVersionControls(f){
  const state=readNewViewVersionState();
  const row=document.createElement('div');
  row.className='new-view-version-row';
  const version=document.createElement('button');
  version.type='button';
  version.className='button-standard new-view-version-toggle';
  version.setAttribute('aria-expanded','false');
  const label=document.createElement('span');
  label.textContent='Version';
  const current=document.createElement('span');
  current.className='new-view-version-current';
  current.textContent='v'+String(state.current||'');
  version.append(label,current);
  version.onclick=event=>{event.stopPropagation();toggleNewViewVersionHistory();version.setAttribute('aria-expanded',newViewVersionHistoryOpen?'true':'false')};
  const update=document.createElement('button');
  update.type='button';
  update.className='button-standard new-view-update-button';
  update.textContent='Update';
  update.disabled=Boolean(state.busy);
  update.onclick=async event=>{
    event.stopPropagation();
    if(update.disabled)return;
    update.disabled=true;
    try{
      if(parent&&parent.UI&&typeof parent.UI.updateToLatestVersion==='function')await parent.UI.updateToLatestVersion();
    }catch(_){}
    finally{update.disabled=false;renderNewViewVersionHistory()}
  };
  row.append(version,update);
  f.appendChild(row);
  const history=document.createElement('div');
  history.className='new-view-version-history';
  history.hidden=true;
  f.appendChild(history);
}'''
if view_np.count(header_marker) != 1:
    raise SystemExit(f'New View header marker: expected 1 match, found {view_np.count(header_marker)}')
view_np = view_np.replace(header_marker, version_helpers + '\n' + header_marker, 1)

header_tail_old = 'fb.setAttribute(\'aria-label\',\'Weapon filter\');fb.onclick=cycleWeaponFilter;f.appendChild(fb)}'
header_tail_new = 'fb.setAttribute(\'aria-label\',\'Weapon filter\');fb.onclick=cycleWeaponFilter;f.appendChild(fb);if(p===\'view\')addNewViewVersionControls(f)}'
if view_np.count(header_tail_old) != 1:
    raise SystemExit(f'New View header tail: expected 1 match, found {view_np.count(header_tail_old)}')
view_np = view_np.replace(header_tail_old, header_tail_new, 1)

# Write the modified New View document back.
view_srcdoc = html.escape(view_np, quote=True)
text = text[:vm.start(2)] + view_srcdoc + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.95
    Scope: Transfer the existing Version / Update interface into New View without duplicating the version engine. New View row 5 now uses the fixed 16-column sheet grid: Version spans A:L and Update spans M:P. Version/current toggles a ten-release history panel rendered as two rows of five; retained-version buttons call the existing parent loadGithubVersion path. Update directly calls the existing updateToLatestVersion path and does not open or close the history panel. The parent exposes only a read-only version UI snapshot; GitHub history refresh, version checkpointing, host mounting, and update behavior remain owned by the existing version system.
    Risk areas: New View version presentation and a read-only parent UI bridge only. Old View Version/Update/Download behavior, release host, roster/model processing, New View lock/frozen snapshot, unified Edit, Cards, persistence, CSV data, Waha routing, and Probable remain unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.94\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

# Retain only the five newest V31 detailed notes.
notes = list(re.finditer(r'\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n', text, re.S))
for match in reversed(notes[5:]):
    text = text[:match.start()] + text[match.end():]

# Final acceptance checks.
vm = view_pat.search(text)
if not vm:
    raise SystemExit('New View iframe missing after writeback')
final_view = html.unescape(vm.group(2))

required_view = [
    '.new-view-version-row{grid-column:1/span 16;grid-row:5;',
    '.new-view-version-toggle{grid-column:1/span 12;',
    '.new-view-update-button{grid-column:13/span 4;',
    '.new-view-version-history{grid-column:1/span 16;grid-row:6/span 2;',
    'grid-template-columns:repeat(5,minmax(0,1fr));',
    'let newViewVersionHistoryOpen=false;',
    'function toggleNewViewVersionHistory(){',
    "if(parent&&parent.UI&&typeof parent.UI.refreshGithubVersionHistory==='function')await parent.UI.refreshGithubVersionHistory();",
    "if(parent&&parent.UI&&typeof parent.UI.updateToLatestVersion==='function')await parent.UI.updateToLatestVersion();",
    "if(p==='view')addNewViewVersionControls(f)",
]
for value in required_view:
    if value not in final_view:
        raise SystemExit('V31.95 New View acceptance failed: ' + value)

required_outer = [
    '<title>WH40k 11th V31.95</title>',
    'const APP_VERSION = "31.95";',
    "version: 'V31.95',",
    'function getVersionUiState() {',
    'getVersionUiState,',
    'CHANGE NOTE - WH40k_11th_V31.95',
]
for value in required_outer:
    if value not in text:
        raise SystemExit('V31.95 acceptance failed: ' + value)

# Existing parent engine must remain intact and New View Update must not reuse the
# Version-toggle handler.
for value in [
    'async function toggleVersionHistory() {',
    'async function updateToLatestVersion() {',
    'async function loadGithubVersion(version) {',
]:
    if value not in text:
        raise SystemExit('V31.95 regressed existing version engine: ' + value)
if "update.onclick=async event=>{\n    event.stopPropagation();" not in final_view:
    raise SystemExit('V31.95 Update click isolation missing')

path.write_text(text, encoding='utf-8')
print('Built V31.95: New View grid Version toggle + direct Update action')
