from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.80.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


once('<title>WH40k 11th V31.80</title>', '<title>WH40k 11th V31.81</title>', 'title')
once('The current baseline is WH40k_11th_V31.80;', 'The current baseline is WH40k_11th_V31.81;', 'baseline')
once('const APP_VERSION = "31.80";', 'const APP_VERSION = "31.81";', 'APP_VERSION')
once("version: 'V31.80',", "version: 'V31.81',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
edit_pat = re.compile(r'(<iframe id="npEditFrame" class="np-view-frame" title="New Edit" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
em = edit_pat.search(text)
if not vm or not em:
    raise SystemExit('New View/New Edit iframe missing')
view_np = html.unescape(vm.group(2))
edit_np = html.unescape(em.group(2))

# Final display-data link for the staged migration: New View now reads its Unit
# records only from New Edit. The complete record already staged in New Edit
# carries name/count/profile stats, Waha, core abilities, Weapons, Weapon stats,
# tags, and Range/Melee/Other scope.
legacy_unit_call = 'parent.getAlternateViewUnitData(index)'
new_edit_unit_call = 'parent.getNewEditUnitData(index)'
if view_np.count(legacy_unit_call) != 1:
    raise SystemExit(f'New View legacy Unit source: expected 1 match, found {view_np.count(legacy_unit_call)}')
if view_np.count(new_edit_unit_call) != 0:
    raise SystemExit(f'New View New Edit Unit source unexpectedly already present: {view_np.count(new_edit_unit_call)}')
view_np = view_np.replace(legacy_unit_call, new_edit_unit_call, 1)

# Write New View back before updating the parent-facing bridge.
text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

# Make the New Edit Unit bridge independently current. New View never falls back
# to Old Edit/model: it asks New Edit to refresh its locally staged copy first,
# then reads only New Edit's local Unit record.
old_parent_unit_bridge = '''    window.getNewEditUnitData = function(index) {
      const frame = document.getElementById("npEditFrame");
      try {
        const editWindow = frame && frame.contentWindow;
        return editWindow && typeof editWindow.getNewEditUnitData === "function"
          ? editWindow.getNewEditUnitData(index)
          : null;
      } catch (_) {
        return null;
      }
    };'''
new_parent_unit_bridge = '''    window.getNewEditUnitData = function(index) {
      const frame = document.getElementById("npEditFrame");
      try {
        const editWindow = frame && frame.contentWindow;
        if (editWindow && typeof editWindow.refreshNewEditUnitsFromLegacy === "function") editWindow.refreshNewEditUnitsFromLegacy();
        return editWindow && typeof editWindow.getNewEditUnitData === "function"
          ? editWindow.getNewEditUnitData(index)
          : null;
      } catch (_) {
        return null;
      }
    };'''
once(old_parent_unit_bridge, new_parent_unit_bridge, 'New Edit parent Unit bridge')

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.81
    Scope: Complete the current New View display-data link to New Edit. New View now reads its Unit records only through getNewEditUnitData(), so Unit name/count/profile stats, Waha URL, core-ability badges/detail, Weapons and Weapon stats, Weapon Tags, and weapon scope/filter data all come from New Edit's locally staged Unit records. The parent-facing New Edit Unit bridge refreshes New Edit's temporary Old Edit/model-fed local copy before returning it, but New View itself has no direct Old Edit/model Unit-data dependency. The title/header remains exclusively linked to New Edit from V31.80. No legacy Edit functionality is otherwise migrated or removed in this phase.
    Risk areas: New View Unit/detail/Weapon data-source boundary only. New Edit's temporary upstream Old Edit/model feed remains intentionally in place. Cards, persistence, CSV data, Waha external routing, Probable, and unrelated UI are unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.80\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.76\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

# Final architecture audit: every piece of New View display data must come from
# New Edit. New Edit may still use the temporary Old Edit/model upstream feed.
vm = view_pat.search(text)
em = edit_pat.search(text)
if not vm or not em:
    raise SystemExit('final New View/New Edit iframe verification failed')
final_view = html.unescape(vm.group(2))
final_edit = html.unescape(em.group(2))

if final_view.count('parent.getNewEditHeaderData()') != 1:
    raise SystemExit(f'New View header must read New Edit exactly once; found {final_view.count("parent.getNewEditHeaderData()")}')
if final_view.count(new_edit_unit_call) != 1:
    raise SystemExit(f'New View Unit data must read New Edit exactly once; found {final_view.count(new_edit_unit_call)}')

# Reject direct legacy/model display-data reads from New View.
for forbidden in [
    'parent.getAlternateViewUnitData',
    'parent.getAlternateViewHeaderData',
    'getAlternateViewHeaderData()',
    'getActiveRoster()',
    'getViewEditRoster()',
    'getRosterPoints(',
    'getCardsTotalVpForRoster(',
    'summaryRest',
    "n.textContent='Winning ORKS'",
    "d.textContent='Bully Boyz - Da Big Hunt - Wreckas'",
    "a.textContent='Priority Assets'",
    "z.textContent='- 1995 pts - 10 VPs'",
]:
    if forbidden in final_view:
        raise SystemExit('New View has an alternate display-data dependency: ' + forbidden)

# Verify the existing New View renderers still consume the full record that New
# Edit owns. These checks cover everything currently visible/used by New View.
for required in [
    "String(data.name||'')",
    "String(data.count??1)",
    'data.m', 'data.t', 'data.sv', 'data.w', 'data.ld', 'data.oc',
    'data.waha',
    'data.coreAbilities',
    'data.weapons',
    'weapon.name', 'weapon.range', 'weapon.attacks', 'weapon.skill',
    'weapon.strength', 'weapon.ap', 'weapon.damage',
    'weapon.tags', 'weapon.scope',
]:
    if required not in final_view:
        raise SystemExit('New View complete display-data contract check failed: ' + required)

# New Edit must still own a local staged copy and remain the only temporary layer
# permitted to read the Old Edit/model Unit bridge.
for required in [
    'let unitDataByIndex=[null,null];',
    'window.getNewEditUnitData=function(index)',
    'parent.getAlternateViewUnitData(index)',
    'refreshAlternateViewUnitsFromParent();',
]:
    if required not in final_edit:
        raise SystemExit('New Edit staged Unit contract check failed: ' + required)

# Parent Unit bridge may only refresh/read the New Edit iframe; no direct Old
# Edit/model fallback is allowed in the New View -> New Edit boundary.
bridge_start = text.index('    window.getNewEditUnitData = function(index) {')
bridge_end = text.index('\n\n    window.getAlternateViewHeaderData = function()', bridge_start)
unit_bridge = text[bridge_start:bridge_end]
for required in [
    'document.getElementById("npEditFrame")',
    'editWindow.refreshNewEditUnitsFromLegacy()',
    'editWindow.getNewEditUnitData(index)',
]:
    if required not in unit_bridge:
        raise SystemExit('New Edit parent Unit bridge check failed: ' + required)
for forbidden in [
    'getAlternateViewUnitData(',
    'getActiveRoster()',
    'getViewEditRoster()',
]:
    if forbidden in unit_bridge:
        raise SystemExit('New View -> New Edit Unit bridge has forbidden fallback: ' + forbidden)

for required in [
    '<title>WH40k 11th V31.81</title>',
    'const APP_VERSION = "31.81";',
    "version: 'V31.81',",
    'CHANGE NOTE - WH40k_11th_V31.81',
]:
    if required not in text:
        raise SystemExit('version acceptance check failed: ' + required)

out.write_text(text, encoding='utf-8')
print('Built V31.81: all current New View display data is sourced from New Edit')
