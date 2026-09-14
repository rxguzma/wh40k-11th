from pathlib import Path
import html
import re

path = Path("WH40k_11th.html")
text = path.read_text(encoding="utf-8")


def replace_once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    text = text.replace(old, new, 1)


replace_once("<title>WH40k 11th V31.129</title>", "<title>WH40k 11th V31.130</title>", "title")
replace_once("The current baseline is WH40k_11th_V31.129;", "The current baseline is WH40k_11th_V31.130;", "baseline")
replace_once('const APP_VERSION = "31.129";', 'const APP_VERSION = "31.130";', "APP_VERSION")
replace_once("version: 'V31.129',", "version: 'V31.130',", "quality version")

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing")
view_np = html.unescape(vm.group(2))

old = "if(selectedWeaponIndex!==null&&!visible.includes(selectedWeaponIndex))selectedWeaponIndex=null;selectedAbilityKey=null;"
new = "if(selectedWeaponIndex!==null&&!visible.includes(selectedWeaponIndex))selectedWeaponIndex=null;"
count = view_np.count(old)
if count != 1:
    raise SystemExit(f"ability click reset bug: expected 1 match, found {count}")
view_np = view_np.replace(old, new, 1)

text = text[:vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.130
    Scope: Fix unified New View Ability buttons not opening when tapped. syncWeaponLayout() was unconditionally clearing selectedAbilityKey because selectedAbilityKey=null sat outside the intended selected-Weapon guard. Remove that unconditional reset so tapping an Ability preserves the selected Ability through the re-render and reveals its Short Description and structured Tags. Weapon selection still clears Ability selection through the existing selectWeapon() path, and filter/unit changes still clear Ability selection through their existing paths.
    Risk areas: Unified New View transient Ability selection only. No Ability data, Old Edit authority, filtering rules, Weapon rendering, Probable, CSV data, persistence, Cards, Waha, lock/report, or layout dimensions changed.
  -->

'''
marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.129\n"
if text.count(marker) != 1:
    raise SystemExit("V31.129 change-note insertion marker missing")
text = text.replace(marker, note + marker, 1)

notes = list(re.finditer(r"\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n", text, re.S))
for match in reversed(notes[5:]):
    text = text[:match.start()] + text[match.end():]

vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing after writeback")
final_view = html.unescape(vm.group(2))
if old in final_view:
    raise SystemExit("V31.130 acceptance failed: unconditional Ability reset remains")
if new not in final_view:
    raise SystemExit("V31.130 acceptance failed: guarded Weapon reset missing")
for expected in [
    "function selectNewViewAbility(key){",
    "selectedAbilityKey=selectedAbilityKey===clean?null:clean;",
    "syncWeaponLayout();",
    "<title>WH40k 11th V31.130</title>",
    "The current baseline is WH40k_11th_V31.130;",
    'const APP_VERSION = "31.130";',
    "version: 'V31.130',",
    "CHANGE NOTE - WH40k_11th_V31.130",
]:
    if expected not in text and expected not in final_view:
        raise SystemExit("V31.130 acceptance failed: " + expected)

path.write_text(text, encoding="utf-8")
print("Built V31.130: Ability selection no longer gets cleared during syncWeaponLayout")
