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


# Sequential release metadata.
replace_once("<title>WH40k 11th V31.138</title>", "<title>WH40k 11th V31.139</title>", "title")
replace_once(
    "The current baseline is WH40k_11th_V31.138;",
    "The current baseline is WH40k_11th_V31.139;",
    "baseline",
)
replace_once('const APP_VERSION = "31.138";', 'const APP_VERSION = "31.139";', "APP_VERSION")
replace_once("version: 'V31.138',", "version: 'V31.139',", "quality version")

view_pat = re.compile(
    r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)',
    re.S,
)
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing")
view_np = html.unescape(vm.group(2))

for required in [
    "/* V31.138 roster-backed Tag state display in unified New View. */",
    "const tagStates=weapon&&Array.isArray(weapon.tagStates)?weapon.tagStates:[];",
    "el.classList.toggle('tag-state-on',Boolean(label)&&tagActive);",
    "el.classList.toggle('tag-state-off',Boolean(label)&&!tagActive);",
    "let selectedWeaponIndex=null;",
]:
    if required not in view_np:
        raise SystemExit("V31.139 baseline contract missing: " + required)

# Weapon Tags stay visually muted until their Weapon is selected. Selection is
# a display gate only: the roster-backed Tag active/locked state remains intact
# and becomes visible only for the selected Weapon. Ability Tags are untouched.
old_weapon_state = '''        const state=tagStates[index]||null;
        const tagActive=state?Boolean(state.active):true;
        el.textContent=label;
        el.style.display=label?'inline-flex':'none';
        el.classList.toggle('tag-state-on',Boolean(label)&&tagActive);
        el.classList.toggle('tag-state-off',Boolean(label)&&!tagActive);
        el.classList.toggle('tag-state-locked',Boolean(label)&&Boolean(state&&state.locked));
        el.dataset.tagActive=tagActive?'true':'false';
        el.dataset.tagLocked=state&&state.locked?'true':'false';'''
new_weapon_state = '''        const state=tagStates[index]||null;
        const tagActive=state?Boolean(state.active):true;
        const weaponSelected=selectedWeaponIndex===i;
        const displayActive=weaponSelected&&tagActive;
        el.textContent=label;
        el.style.display=label?'inline-flex':'none';
        el.classList.toggle('tag-state-on',Boolean(label)&&displayActive);
        el.classList.toggle('tag-state-off',Boolean(label)&&!displayActive);
        el.classList.toggle('tag-state-locked',Boolean(label)&&Boolean(state&&state.locked));
        el.dataset.tagActive=tagActive?'true':'false';
        el.dataset.tagLocked=state&&state.locked?'true':'false';
        el.dataset.weaponSelected=weaponSelected?'true':'false';'''
if view_np.count(old_weapon_state) != 1:
    raise SystemExit(f"Weapon Tag state renderer: expected 1 match, found {view_np.count(old_weapon_state)}")
view_np = view_np.replace(old_weapon_state, new_weapon_state, 1)

text = text[: vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2) :]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.139
    Scope: Unified New View Weapon Tag presentation only. Every Weapon Tag remains in the existing muted Tag treatment while no Weapon is selected. When a Weapon is selected, only that Weapon's Tags are allowed to reveal their existing roster-backed active state; active Tags use the existing active/orange treatment and inactive Tags remain muted. Deselecting or switching Weapons immediately returns non-selected Weapon Tags to muted. Ability Tag state/display is unchanged. No Tag data, Tag writes, persistence, calculations, grid/layout, sizing, borders, filters, focus behavior, or Weapon selection behavior changes.
    Risk areas: Unified New View Weapon Tag visual gating by selected Weapon only. No Ability Tag behavior, CSV data, roster mutation, Probable, lock/FIX, Boyz data, Cards, Waha, Edit, or persistence behavior changed.
  -->

'''
marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.138\n"
if text.count(marker) != 1:
    raise SystemExit("V31.138 change-note insertion marker missing")
text = text.replace(marker, note + marker, 1)

# Keep only the five newest detailed V31 change notes.
notes = list(
    re.finditer(
        r"\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n",
        text,
        re.S,
    )
)
for match in reversed(notes[5:]):
    text = text[: match.start()] + text[match.end() :]

# Focused acceptance checks.
vm = view_pat.search(text)
if not vm:
    raise SystemExit("Unified New View/Edit iframe missing after writeback")
final_view = html.unescape(vm.group(2))
for expected in [
    "const weaponSelected=selectedWeaponIndex===i;",
    "const displayActive=weaponSelected&&tagActive;",
    "el.classList.toggle('tag-state-on',Boolean(label)&&displayActive);",
    "el.classList.toggle('tag-state-off',Boolean(label)&&!displayActive);",
    "el.dataset.weaponSelected=weaponSelected?'true':'false';",
    "/* V31.138 roster-backed Tag state display in unified New View. */",
    "const tagActive=Boolean(tag&&tag.active);",
]:
    if expected not in final_view:
        raise SystemExit("V31.139 View acceptance failed: " + expected)

# Ensure Weapon Tags can no longer expose active styling solely from roster state
# while preserving the underlying active value and Ability Tag renderer.
if "el.classList.toggle('tag-state-on',Boolean(label)&&tagActive);" in final_view:
    raise SystemExit("V31.139 obsolete ungated Weapon Tag active styling remains")

for expected in [
    "<title>WH40k 11th V31.139</title>",
    "The current baseline is WH40k_11th_V31.139;",
    'const APP_VERSION = "31.139";',
    "version: 'V31.139',",
    "CHANGE NOTE - WH40k_11th_V31.139",
]:
    if expected not in text:
        raise SystemExit("V31.139 release acceptance failed: " + expected)

path.write_text(text, encoding="utf-8")
print("Built V31.139: Weapon Tags stay muted until their Weapon is selected")
