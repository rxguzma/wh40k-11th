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


once('<title>WH40k 11th V31.111</title>', '<title>WH40k 11th V31.112</title>', 'title')
once('The current baseline is WH40k_11th_V31.111;', 'The current baseline is WH40k_11th_V31.112;', 'baseline')
once('const APP_VERSION = "31.111";', 'const APP_VERSION = "31.112";', 'APP_VERSION')
once("version: 'V31.111',", "version: 'V31.112',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('Unified New View/Edit iframe missing')
view_np = html.unescape(vm.group(2))

old = r'''  const expansionRows=activeUnitIndex===null?0:(showWeapons?nextRow-detailStartRow:1);
  syncExpandedLayout(expansionRows);
}
function cycleWeaponFilter(){'''
new = r'''  const expansionRows=activeUnitIndex===null?0:(showWeapons?nextRow-detailStartRow:1);
  syncExpandedLayout(expansionRows);

  // Re-anchor the expanded detail stack after the roster's final reflow.
  // Switching directly from another open Unit can move the new active Unit
  // upward when the previous expansion collapses; detail rows must follow
  // the Unit's final row, not its pre-reflow row.
  if(activeUnitIndex!==null){
    const finalActiveUnitRow=unitRow(activeUnitIndex);
    const finalActiveRow=finalActiveUnitRow?parseInt(finalActiveUnitRow.style.gridRow||getComputedStyle(finalActiveUnitRow).gridRowStart,10):activeRow;
    const finalDetailStartRow=(Number.isFinite(finalActiveRow)?finalActiveRow:activeRow)+1;
    const finalDetailRow=grid.querySelector('.detail-box-row');
    if(finalDetailRow)finalDetailRow.style.gridRow=String(finalDetailStartRow);
    if(header&&showWeapons)header.style.gridRow=String(finalDetailStartRow+1);
    let finalNextRow=finalDetailStartRow+2;
    if(showWeapons){
      ordered.forEach(i=>{
        const weaponRow=grid.querySelector('.weapon-row-'+i);
        const tagRow=grid.querySelector('.weapon-tags-'+i);
        if(!weaponRow||weaponRow.style.display==='none')return;
        weaponRow.style.gridRow=String(finalNextRow++);
        if(tagRow&&tagRow.style.display!=='none')tagRow.style.gridRow=String(finalNextRow++);
      });
    }
    syncNewViewFrameHeight();
  }
}
function cycleWeaponFilter(){'''
count = view_np.count(old)
if count != 1:
    raise SystemExit(f'Unit-detail layout anchor: expected 1 match, found {count}')
view_np = view_np.replace(old, new, 1)

text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.112
    Scope: Remove the blank grid row that can appear between an opened Unit row and its Unit-level Tags/Waha detail row in unified New View. Expanded detail rows are now re-anchored after the roster finishes its final expansion/collapse reflow, so switching directly from another open Unit cannot leave the detail stack attached to the Unit's stale pre-reflow row. The Unit detail row remains immediately below the active Unit, followed by the existing Weapon header, Weapon rows, and Tag rows with unchanged grid sizing, fonts, colors, and controls.
    Risk areas: Unified New View expanded-Unit row positioning only. No roster data, Unit/Weapon content, Tag rendering, filter logic, Lock prepared-state behavior, report wrench, unified Edit, Version/Update/Download, Cards, persistence, CSV data, Waha routing, or Probable logic changes.
  -->

'''
mark = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.111
'''
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

notes = list(re.finditer(r'\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n', text, re.S))
for match in reversed(notes[5:]):
    text = text[:match.start()] + text[match.end():]

for required in [
    '<title>WH40k 11th V31.112</title>',
    'The current baseline is WH40k_11th_V31.112;',
    'const APP_VERSION = "31.112";',
    "version: 'V31.112',",
    'CHANGE NOTE - WH40k_11th_V31.112',
    'const finalDetailStartRow=(Number.isFinite(finalActiveRow)?finalActiveRow:activeRow)+1;',
]:
    if required not in text:
        raise SystemExit('V31.112 acceptance failed: ' + required)

for forbidden in ['id="newEditPageScreen"', 'id="npEditFrame"', 'parent.getNewEdit']:
    if forbidden in text:
        raise SystemExit('V31.112 regressed retired standalone New Edit: ' + forbidden)

path.write_text(text, encoding='utf-8')
print('Built V31.112: expanded Unit detail stack re-anchored after roster reflow')
