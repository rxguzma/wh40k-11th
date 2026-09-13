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
once('<title>WH40k 11th V31.96</title>', '<title>WH40k 11th V31.97</title>', 'title')
once('The current baseline is WH40k_11th_V31.96;', 'The current baseline is WH40k_11th_V31.97;', 'baseline')
once('const APP_VERSION = "31.96";', 'const APP_VERSION = "31.97";', 'APP_VERSION')
once("version: 'V31.96',", "version: 'V31.97',", 'quality version')

# ---------------------------------------------------------------------------
# New View: make Version / Update / Download true children of the main 16-cell
# sheet grid. Remove the nested strip/sub-grid, strip background, and overlay
# z-index. History buttons are also direct main-grid children.
# ---------------------------------------------------------------------------
view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('New View iframe missing')
view_np = html.unescape(vm.group(2))

old_css = r'''.new-view-version-row{grid-column:1/span 16;z-index:130;display:grid;grid-template-columns:repeat(16,var(--cell));height:var(--cell);align-items:center;background:var(--bg)}
.new-view-version-toggle{grid-column:1/span 8;justify-self:center;justify-content:space-between}
.new-view-version-current{color:var(--muted)}
.new-view-update-button{grid-column:9/span 4;justify-self:center}
.new-view-download-button{grid-column:13/span 4;justify-self:center;text-decoration:none}
.new-view-download-button[aria-disabled="true"]{opacity:.5}
.new-view-version-history{grid-column:1/span 16;z-index:130;width:100%;height:calc(var(--cell)*2);padding:1px;display:grid;grid-template-columns:repeat(5,minmax(0,1fr));grid-template-rows:repeat(2,var(--std));gap:var(--gap);background:var(--card);border:1px solid var(--border)}
.new-view-version-history[hidden]{display:none!important}
.new-view-version-option{width:100%;padding:0 2px;font-size:11px}
.new-view-version-option:disabled{opacity:1}'''
new_css = r'''.new-view-version-toggle{grid-column:1/span 8;justify-self:stretch;align-self:center;justify-content:space-between}
.new-view-version-current{color:var(--muted)}
.new-view-update-button{grid-column:9/span 4;justify-self:stretch;align-self:center}
.new-view-download-button{grid-column:13/span 4;justify-self:stretch;align-self:center;text-decoration:none}
.new-view-download-button[aria-disabled="true"]{opacity:.5}
.new-view-version-option{justify-self:stretch;align-self:center;width:100%;padding:0 2px;font-size:11px}
.new-view-version-option:disabled{opacity:1}'''
if view_np.count(old_css) != 1:
    raise SystemExit(f'V31.96 New View version CSS: expected 1 match, found {view_np.count(old_css)}')
view_np = view_np.replace(old_css, new_css, 1)

helpers_pat = re.compile(r"let newViewVersionHistoryOpen=false;\n.*?\nfunction addViewHeader\(f,p\)", re.S)
hm = helpers_pat.search(view_np)
if not hm:
    raise SystemExit('V31.96 New View version helper block missing')

new_helpers = r'''let newViewVersionHistoryOpen=false;
let newViewVersionObserver=null;
const NEW_VIEW_VERSION_HISTORY_COLUMNS=['1 / span 3','4 / span 3','7 / span 4','11 / span 3','14 / span 3'];
function readNewViewVersionState(){
  try{
    if(parent&&parent.UI&&typeof parent.UI.getVersionUiState==='function')return parent.UI.getVersionUiState()||{};
  }catch(_){}
  return {};
}
function getNewViewVersionRow(){
  let lastUnitRow=0;
  grid.querySelectorAll('.view-unit-row.dynamic-roster-row').forEach(unit=>{
    const value=Number(unit.style.gridRow||0);
    if(Number.isFinite(value))lastUnitRow=Math.max(lastUnitRow,value);
  });
  const firstUnitRow=typeof FIRST_UNIT_ROW==='number'?FIRST_UNIT_ROW:7;
  return (lastUnitRow||(firstUnitRow-1))+5;
}
function positionNewViewVersionControls(){
  const versionRow=getNewViewVersionRow();
  const rowValue=String(versionRow);
  const version=grid.querySelector('.new-view-version-toggle');
  const update=grid.querySelector('.new-view-update-button');
  const download=grid.querySelector('.new-view-download-button');
  [version,update,download].forEach(control=>{if(control&&control.style.gridRow!==rowValue)control.style.gridRow=rowValue;});
  grid.querySelectorAll('.new-view-version-option').forEach((button,index)=>{
    button.style.gridRow=String(versionRow+1+Math.floor(index/5));
    button.style.gridColumn=NEW_VIEW_VERSION_HISTORY_COLUMNS[index%5];
  });
  return versionRow;
}
function newViewVersionMutationTouchesLayout(mutation){
  if(mutation.type==='attributes'){
    const target=mutation.target;
    return Boolean(target&&target.classList&&target.classList.contains('dynamic-roster-row'));
  }
  if(mutation.type!=='childList')return false;
  const nodes=[...mutation.addedNodes,...mutation.removedNodes];
  return nodes.some(node=>node&&node.nodeType===1&&(
    (node.classList&&node.classList.contains('dynamic-roster-row')) ||
    (typeof node.querySelector==='function'&&Boolean(node.querySelector('.dynamic-roster-row')))
  ));
}
function ensureNewViewVersionObserver(){
  if(newViewVersionObserver)return;
  newViewVersionObserver=new MutationObserver(mutations=>{
    if(mutations.some(newViewVersionMutationTouchesLayout))positionNewViewVersionControls();
  });
  newViewVersionObserver.observe(grid,{childList:true,subtree:true,attributes:true,attributeFilter:['style']});
}
function clearNewViewVersionHistoryButtons(){
  grid.querySelectorAll('.new-view-version-option').forEach(button=>button.remove());
}
function renderNewViewVersionHistory(){
  clearNewViewVersionHistoryButtons();
  if(!newViewVersionHistoryOpen)return;
  const state=readNewViewVersionState();
  const current=String(state.current||'');
  const entries=Array.isArray(state.entries)?state.entries.slice(0,10):[];
  const versionRow=getNewViewVersionRow();
  entries.forEach((entry,index)=>{
    const version=String(entry&&entry.version||'');
    if(!version)return;
    const b=document.createElement('button');
    b.type='button';
    b.className='button-standard new-view-version-option'+(version===current?' active-green':'');
    b.textContent='v'+version;
    b.disabled=version===current||Boolean(state.busy);
    b.style.gridRow=String(versionRow+1+Math.floor(index/5));
    b.style.gridColumn=NEW_VIEW_VERSION_HISTORY_COLUMNS[index%5];
    b.onclick=event=>{event.stopPropagation();if(b.disabled)return;try{parent.UI.loadGithubVersion(version)}catch(_){}};
    grid.appendChild(b);
  });
}
async function toggleNewViewVersionHistory(){
  newViewVersionHistoryOpen=!newViewVersionHistoryOpen;
  renderNewViewVersionHistory();
  const version=grid.querySelector('.new-view-version-toggle');
  if(version)version.setAttribute('aria-expanded',newViewVersionHistoryOpen?'true':'false');
  if(!newViewVersionHistoryOpen)return;
  try{
    if(parent&&parent.UI&&typeof parent.UI.refreshGithubVersionHistory==='function')await parent.UI.refreshGithubVersionHistory();
  }catch(_){}
  renderNewViewVersionHistory();
}
function addNewViewVersionControls(f){
  const state=readNewViewVersionState();
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
  version.onclick=event=>{event.stopPropagation();toggleNewViewVersionHistory()};
  f.appendChild(version);

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
  f.appendChild(update);

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
  f.appendChild(download);

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
    CHANGE NOTE - WH40k_11th_V31.97
    Scope: Integrate New View Version / Update / Download into the actual 16-column sheet grid instead of rendering them inside a separate nested strip. The wrapper, strip background, and overlay z-index are removed. Version is a direct main-grid item at A:H, Update at I:L, and Download at M:P. Their grid row remains exactly five rows after the last rendered Unit and automatically follows Unit row changes. When Version is opened, the ten retained release buttons are also direct main-grid items across two rows of five rather than children of an overlay panel. Existing version, update, retained-release, and download functions remain unchanged.
    Risk areas: New View version-control presentation only. Existing parent version engine, Old View, roster/model data, New View lock/frozen snapshot, unified Edit, Cards, persistence, CSV data, Waha routing, and Probable remain unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.96\n'
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
    '.new-view-version-toggle{grid-column:1/span 8;justify-self:stretch;',
    '.new-view-update-button{grid-column:9/span 4;justify-self:stretch;',
    '.new-view-download-button{grid-column:13/span 4;justify-self:stretch;',
    "const NEW_VIEW_VERSION_HISTORY_COLUMNS=['1 / span 3','4 / span 3','7 / span 4','11 / span 3','14 / span 3'];",
    "return (lastUnitRow||(firstUnitRow-1))+5;",
    "const version=grid.querySelector('.new-view-version-toggle');",
    "grid.querySelectorAll('.new-view-version-option').forEach((button,index)=>{",
    "grid.appendChild(b);",
    "f.appendChild(version);",
    "f.appendChild(update);",
    "f.appendChild(download);",
    "if(parent&&parent.UI&&typeof parent.UI.downloadRunningVersion==='function')return parent.UI.downloadRunningVersion(event);",
]
for value in required_view:
    if value not in final_view:
        raise SystemExit('V31.97 New View acceptance failed: ' + value)

for forbidden in [
    '.new-view-version-row{',
    '.new-view-version-history{',
    "row.className='new-view-version-row'",
    "history.className='new-view-version-history'",
    'z-index:130',
    'background:var(--bg)',
]:
    if forbidden in final_view:
        raise SystemExit('V31.97 separate/overlay version layout remains: ' + forbidden)

required_outer = [
    '<title>WH40k 11th V31.97</title>',
    'const APP_VERSION = "31.97";',
    "version: 'V31.97',",
    'downloadBusy: Boolean(versionDownloadBusy),',
    'downloadUrl: APP_DOWNLOAD_DATA.url,',
    'downloadFilename: APP_DOWNLOAD_DATA.filename,',
    'async function updateToLatestVersion() {',
    'downloadRunningVersion,',
    'CHANGE NOTE - WH40k_11th_V31.97',
]
for value in required_outer:
    if value not in text:
        raise SystemExit('V31.97 acceptance failed: ' + value)

path.write_text(text, encoding='utf-8')
print('Built V31.97: native main-grid Version / Update / Download controls')
