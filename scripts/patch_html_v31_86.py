from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.85.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


once('<title>WH40k 11th V31.85</title>', '<title>WH40k 11th V31.86</title>', 'title')
once('The current baseline is WH40k_11th_V31.85;', 'The current baseline is WH40k_11th_V31.86;', 'baseline')
once('const APP_VERSION = "31.85";', 'const APP_VERSION = "31.86";', 'APP_VERSION')
once("version: 'V31.85',", "version: 'V31.86',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('New View iframe missing')
view_np = html.unescape(vm.group(2))

# The View weapon filter is user state. Opening/closing a Unit or refreshing
# Unit data must not mutate it. ALL remains only the initial page-load default.
toggle_old = '''function toggleUnitDetails(index){
  const next=activeUnitIndex===index?null:index;
  activeUnitIndex=next;
  weaponFilterMode='ALL';
  selectedWeaponIndex=null;
  applyActiveUnitDetails();
  syncUnitDetailVisibility();
}'''
toggle_new = '''function toggleUnitDetails(index){
  const next=activeUnitIndex===index?null:index;
  activeUnitIndex=next;
  selectedWeaponIndex=null;
  applyActiveUnitDetails();
  syncUnitDetailVisibility();
}'''
if view_np.count(toggle_old) != 1:
    raise SystemExit(f'Unit-toggle filter reset: expected 1 match, found {view_np.count(toggle_old)}')
view_np = view_np.replace(toggle_old, toggle_new, 1)

refresh_old = '''  activeUnitIndex=null;
  weaponFilterMode='ALL';
  selectedWeaponIndex=null;
  applyActiveUnitDetails();'''
refresh_new = '''  activeUnitIndex=null;
  selectedWeaponIndex=null;
  applyActiveUnitDetails();'''
if view_np.count(refresh_old) != 1:
    raise SystemExit(f'View-refresh filter reset: expected 1 match, found {view_np.count(refresh_old)}')
view_np = view_np.replace(refresh_old, refresh_new, 1)

# Verify the filter can now change only through its own carousel logic after
# initial page construction.
if view_np.count("let weaponFilterMode='ALL';") != 1:
    raise SystemExit('initial ALL default missing or duplicated')
if "weaponFilterMode=weaponFilterModes[(index+1)%weaponFilterModes.length];" not in view_np:
    raise SystemExit('filter carousel assignment missing')

toggle_match = re.search(r'function toggleUnitDetails\(index\)\{(.*?)\n\}', view_np, re.S)
refresh_match = re.search(r'function refreshAlternateViewUnitsFromParent\(\)\{(.*?)\n\}', view_np, re.S)
if not toggle_match or not refresh_match:
    raise SystemExit('View Unit controller verification failed')
for body, label in [(toggle_match.group(1), 'Unit toggle'), (refresh_match.group(1), 'Unit refresh')]:
    if 'weaponFilterMode=' in body:
        raise SystemExit(f'{label} still changes weaponFilterMode')

if 'parent.getNewEditUnitData(index)' not in view_np:
    raise SystemExit('New View Unit source changed unexpectedly')

text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.86
    Scope: Preserve the New View ALL / SHOOT / MELEE / OTHER filter across Unit open/close toggles and Unit-data refreshes. The filter now changes only when the user taps the filter control; ALL remains the initial page-load default. Unit toggling may still clear an individual Weapon selection, but it no longer changes the top filter. New View continues to source Unit data through New Edit.
    Risk areas: New View weapon-filter state only. New Edit, Unit data, Weapons, Tags, Waha routing, Cards, persistence, CSV data, and Probable are unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.85\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.81\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

for required in [
    '<title>WH40k 11th V31.86</title>',
    'const APP_VERSION = "31.86";',
    "version: 'V31.86',",
    'CHANGE NOTE - WH40k_11th_V31.86',
]:
    if required not in text:
        raise SystemExit('version acceptance failed: ' + required)

out.write_text(text, encoding='utf-8')
print('Built V31.86: New View weapon filter persists across Unit toggles and refreshes')
