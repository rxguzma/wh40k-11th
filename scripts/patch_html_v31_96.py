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
once('<title>WH40k 11th V31.95</title>', '<title>WH40k 11th V31.96</title>', 'title')
once('The current baseline is WH40k_11th_V31.95;', 'The current baseline is WH40k_11th_V31.96;', 'baseline')
once('const APP_VERSION = "31.95";', 'const APP_VERSION = "31.96";', 'APP_VERSION')
once("version: 'V31.95',", "version: 'V31.96',", 'quality version')

# ---------------------------------------------------------------------------
# Existing version engine bridge: expose the already-prepared download target
# and busy state so New View can use the exact existing download path.
# ---------------------------------------------------------------------------
old_getter = '''    function getVersionUiState() {
      return {
        current: APP_VERSION,
        busy: Boolean(versionActionBusy),
        entries: versionHistoryEntries.map(entry => ({ version: String(entry && entry.version || "") })).filter(entry => entry.version)
      };
    }'''
new_getter = '''    function getVersionUiState() {
      return {
        current: APP_VERSION,
        busy: Boolean(versionActionBusy),
        downloadBusy: Boolean(versionDownloadBusy),
        downloadUrl: APP_DOWNLOAD_DATA.url,
        downloadFilename: APP_DOWNLOAD_DATA.filename,
        entries: versionHistoryEntries.map(entry => ({ version: String(entry && entry.version || "") })).filter(entry => entry.version)
      };
    }'''
once(old_getter, new_getter, 'version UI download state bridge')

# ---------------------------------------------------------------------------
# New View: remove the V31.95 fixed row-5 placement, add Download, and position
# the whole control strip at the bottom. Normal/collapsed placement is exactly
# five grid rows after the last Unit. The existing main-button position is also
# respected so an expanded final Unit can never overlap the version controls.
# ---------------------------------------------------------------------------
view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('New View iframe missing')
view_np = html.unescape(vm.group(2))

old_css = r'''.new-view-version-row{grid-column:1/span 16;grid-row:5;z-index:130;display:grid;grid-template-columns:repeat(16,var(--cell));height:var(--cell);align-items:center;background:var(--bg)}
.new-view-version-toggle{grid-column:1/span 12;justify-self:center;justify-content:space-between}
.new-view-version-current{color:var(--muted)}
.new-view-update-button{grid-column:13/span 4;justify-self:center}
.new-view-version-history{grid-column:1/span 16;grid-row:6/span 2;z-index:130;width:100%;height:calc(var(--cell)*2);padding:1px;display:grid;grid-template-columns:repeat(5,minmax(0,1fr));grid-template-rows:repeat(2,var(--std));gap:var(--gap);background:var(--card);border:1px solid var(--border)}
.new-view-version-history[hidden]{display:none!important}
.new-view-version-option{width:100%;padding:0 2px;font-size:11px}
.new-view-version-option:disabled{opacity:1}'''
new_css = r'''.new-view-version-row{grid-column:1/span 16;z-index:130;display:grid;grid-template-columns:repeat(16,var(--cell));height:var(--cell);align-items:center;background:var(--bg)}
.new-view-version-toggle{grid-column:1/span 8;justify-self:center;justify-content:space-between}
.new-view-version-current{color:var(--muted)}
.new-view-update-button{grid-column:9/span 4;justify-self:center}
.new-view-download-button{grid-column:13/span 4;justify-self:center;text-decoration:none}
.new-view-download-button[aria-disabled="true"]{opacity:.5}
.new-view-version-history{grid-column:1/span 16;z-index:130;width:100%;height:calc(var(--cell)*2);padding:1px;display:grid;grid-template-columns:repeat(5,minmax(0,1fr));grid-template-rows:repeat(2,var(--std));gap:var(--gap);background:var(--card);border:1px solid var(--border)}
.new-view-version-history[hidden]{display:none!important}
.new-view-version-option{width:100%;padding:0 2px;font-size:11px}
.new-view-version-option:disabled{opacity:1}'''
if view_np.count(old_css) != 1:
    raise SystemExit(f'V31.95 New View version CSS: expected 1 match, found {view_np.count(old_css)}')
view_np = view_np.replace(old_css, new_css, 1)

helpers_pat = re.compile(r"let newViewVersionHistoryOpen=false;\n.*?\nfunction addViewHeader\(f,p\)", re.S)
hm = helpers_pat.search(view_np)
if not hm:
    raise SystemExit('V31.95 New View version helper block missing')
new_helpers = r'''let newViewVersionHistoryOpen=false;
let newViewVersionObserver=null;
function readNewViewVersionState(){
  try{
    if(parent&&parent.UI&&typeof parent.UI.getVersionUiState==='function')return parent.UI.getVersionUiState()||{};
  }catch(_){}
  return {};
}
function positionNewViewVersionControls(){
  const row=grid.querySelector('.new-view-version-row');
  const history=grid.querySelector('.new-view-version-history');
  if(!row)return 0;
  let lastUnitRow=0;
  grid.querySelectorAll('.view-unit-row.dynamic-roster-row').forEach(unit=>{
    const value=Number(unit.style.gridRow||0);
    if(Number.isFinite(value))lastUnitRow=Math.max(lastUnitRow,value);
  });
  const firstUnitRow=typeof FIRST_UNIT_ROW==='number'?FIRST_UNIT_ROW:7;
  const unitBasedRow=(lastUnitRow||(firstUnitRow-1))+5;
  const mainButton=grid.querySelector('.top-main-button');
  const mainButtonRow=mainButton?Number(mainButton.style.gridRow||0):0;
  const versionRow=Math.max(unitBasedRow,Number.isFinite(mainButtonRow)&&mainButtonRow>0?mainButtonRow+3:0);
  const rowValue=String(versionRow);
  if(row.style.gridRow!==rowValue)row.style.gridRow=rowValue;
  if(history){
    const historyValue=String(versionRow+1)+' / span 2';
    if(history.style.gridRow!==historyValue)history.style.gridRow=historyValue;
  }
  return versionRow;
}
function newViewVersionMutationTouchesLayout(mutation){
  if(mutation.type==='attributes'){
    const target=mutation.target;
    return Boolean(target&&target.classList&&(target.classList.contains('dynamic-roster-row')||target.classList.contains('top-main-button')));
  }
  if(mutation.type!=='childList')return false;
  const nodes=[...mutation.addedNodes,...mutation.removedNodes];
  return nodes.some(node=>node&&node.nodeType===1&&(
    (node.classList&&(node.classList.contains('dynamic-roster-row')||node.classList.contains('top-main-button'))) ||
    (typeof node.querySelector==='function'&&Boolean(node.querySelector('.dynamic-roster-row,.top-main-button')))
  ));
}
function ensureNewViewVersionObserver(){
  if(newViewVersionObserver)return;
  newViewVersionObserver=new MutationObserver(mutations=>{
    if(mutations.some(newViewVersionMutationTouchesLayout))positionNewViewVersionControls();
  });
  newViewVersionObserver.observe(grid,{childList:true,subtree:true,attributes:true,attributeFilter:['style']});
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
  positionNewViewVersionControls();
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
  const download=document.createElement('a');
  download.className='button-standard new-view-download-button';
  download.textContent='Download';
  download.href=String(state.downloadUrl||'#');
  download.download=String(state.downloadFilename||'');
  download.target='_blank';
  download.rel='noopener';
  download.setAttribute('aria-disabled',Boolean(state.downloadBusy)?'true':'false');
  download.onclick=event=>{
    event.stopPropagation();
    if(download.getAttribute('aria-disabled')==='true'){event.preventDefault();return false;}
    try{
      if(parent&&parent.UI&&typeof parent.UI.downloadRunningVersion==='function')return parent.UI.downloadRunningVersion(event);
    }catch(_){}
    return true;
  };
  row.append(version,update,download);
  f.appendChild(row);
  const history=document.createElement('div');
  history.className='new-view-version-history';
  history.hidden=true;
  f.appendChild(history);
  ensureNewViewVersionObserver();
  positionNewViewVersionControls();
  requestAnimationFrame(positionNewViewVersionControls);
}
function addViewHeader(f,p)'''
view_np = view_np[:hm.start()] + new_helpers + view_np[hm.end():]

# Write the modified New View document back.
view_srcdoc = html.escape(view_np, quote=True)
text = text[:vm.start(2)] + view_srcdoc + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.96
    Scope: Correct New View Version placement and restore the omitted Download action. The Version / Update / Download strip is no longer fixed near the top. In normal/collapsed View it is positioned exactly five grid rows after the last rendered Unit row and automatically follows Unit additions/removals/reordering. The existing main-button row is also respected so an expanded final Unit cannot overlap the strip. Version spans A:H and toggles retained history; Update spans I:L and directly runs the existing update-to-latest path; Download spans M:P and calls the existing downloadRunningVersion path with the existing prepared URL/filename so iPhone/Safari Save/Share behavior is preserved. Retained history remains two rows of five.
    Risk areas: New View bottom version-strip placement and Download presentation only. Existing version/update/download engine, Old View, roster/model data, New View lock/frozen snapshot, unified Edit, Cards, persistence, CSV data, Waha routing, and Probable remain unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.95\n'
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
    '.new-view-version-row{grid-column:1/span 16;z-index:130;',
    '.new-view-version-toggle{grid-column:1/span 8;',
    '.new-view-update-button{grid-column:9/span 4;',
    '.new-view-download-button{grid-column:13/span 4;',
    '.new-view-version-history{grid-column:1/span 16;z-index:130;',
    'function positionNewViewVersionControls(){',
    "grid.querySelectorAll('.view-unit-row.dynamic-roster-row')",
    "const unitBasedRow=(lastUnitRow||(firstUnitRow-1))+5;",
    "const versionRow=Math.max(unitBasedRow,Number.isFinite(mainButtonRow)&&mainButtonRow>0?mainButtonRow+3:0);",
    'function ensureNewViewVersionObserver(){',
    "download.className='button-standard new-view-download-button';",
    "if(parent&&parent.UI&&typeof parent.UI.downloadRunningVersion==='function')return parent.UI.downloadRunningVersion(event);",
    'grid-template-columns:repeat(5,minmax(0,1fr));',
]
for value in required_view:
    if value not in final_view:
        raise SystemExit('V31.96 New View acceptance failed: ' + value)

for forbidden in [
    '.new-view-version-row{grid-column:1/span 16;grid-row:5;',
    '.new-view-version-toggle{grid-column:1/span 12;',
    '.new-view-update-button{grid-column:13/span 4;',
    '.new-view-version-history{grid-column:1/span 16;grid-row:6/span 2;',
]:
    if forbidden in final_view:
        raise SystemExit('V31.96 fixed-top version layout remains: ' + forbidden)

required_outer = [
    '<title>WH40k 11th V31.96</title>',
    'const APP_VERSION = "31.96";',
    "version: 'V31.96',",
    'downloadBusy: Boolean(versionDownloadBusy),',
    'downloadUrl: APP_DOWNLOAD_DATA.url,',
    'downloadFilename: APP_DOWNLOAD_DATA.filename,',
    'async function updateToLatestVersion() {',
    'downloadRunningVersion,',
    'CHANGE NOTE - WH40k_11th_V31.96',
]
for value in required_outer:
    if value not in text:
        raise SystemExit('V31.96 acceptance failed: ' + value)

path.write_text(text, encoding='utf-8')
print('Built V31.96: bottom Version / Update / Download strip follows last Unit + 5 rows')
