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
replace_once("<title>WH40k 11th V31.139</title>", "<title>WH40k 11th V31.140</title>", "title")
replace_once(
    "The current baseline is WH40k_11th_V31.139;",
    "The current baseline is WH40k_11th_V31.140;",
    "baseline",
)
replace_once('const APP_VERSION = "31.139";', 'const APP_VERSION = "31.140";', "APP_VERSION")
replace_once("version: 'V31.139',", "version: 'V31.140',", "quality version")

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
    "const weaponSelected=selectedWeaponIndex===i;",
    "const displayActive=weaponSelected&&tagActive;",
    "tags.className='unit-ability-tags';",
    "badge.className='weapon-tag '+(tagActive?'tag-state-on':'tag-state-off')+(tag&&tag.locked?' tag-state-locked':'');",
]:
    if required not in view_np:
        raise SystemExit("V31.140 baseline contract missing: " + required)

# Ability Tag state is authoritative for Ability Tags. Give those badges an
# explicit ownership marker so Weapon-selection presentation can never demote
# an Ability Tag that is roster-backed ON, nor promote one that is OFF.
old_badge_class = "badge.className='weapon-tag '+(tagActive?'tag-state-on':'tag-state-off')+(tag&&tag.locked?' tag-state-locked':'');"
new_badge_class = "badge.className='weapon-tag ability-tag-state '+(tagActive?'tag-state-on':'tag-state-off')+(tag&&tag.locked?' tag-state-locked':'');"
if view_np.count(old_badge_class) != 1:
    raise SystemExit(f"Ability Tag badge state class: expected 1 match, found {view_np.count(old_badge_class)}")
view_np = view_np.replace(old_badge_class, new_badge_class, 1)

# Keep the existing V31.138 Tag palette, then explicitly restate Ability Tag
# precedence at higher specificity. This is presentation precedence only; it
# does not alter the roster-backed state, calculations, or Weapon selection.
state_css = r'''/* V31.138 roster-backed Tag state display in unified New View. */
.weapon-tags .weapon-tag.tag-state-on,.unit-ability-tags .weapon-tag.tag-state-on{background:var(--btn)!important;color:var(--orange)!important}
.weapon-tags .weapon-tag.tag-state-off,.unit-ability-tags .weapon-tag.tag-state-off{background:rgba(154,160,166,.5)!important;color:var(--muted)!important}'''
precedence_css = state_css + r'''

/* V31.140 Ability Tag state outranks Weapon-selection muting. */
.unit-ability-tags .weapon-tag.ability-tag-state.tag-state-on{background:var(--btn)!important;color:var(--orange)!important;opacity:1!important}
.unit-ability-tags .weapon-tag.ability-tag-state.tag-state-off{background:rgba(154,160,166,.5)!important;color:var(--muted)!important;opacity:1!important}'''
if view_np.count(state_css) != 1:
    raise SystemExit(f"V31.138 Tag state CSS: expected 1 match, found {view_np.count(state_css)}")
view_np = view_np.replace(state_css, precedence_css, 1)

text = text[: vm.start(2)] + html.escape(view_np, quote=True) + text[vm.end(2) :]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.140
    Scope: Unified New View Tag presentation precedence only. Ability Tags now carry an explicit Ability-owned state marker and their roster-backed On/Off state always outranks the Weapon-selection muting rule: an Ability Tag that is On uses the existing active Tag treatment even when no Weapon is selected; an Ability Tag that is Off remains in the existing muted treatment. V31.139 remains authoritative for ordinary Weapon Tags, which stay muted until their own Weapon is selected and then reveal their roster-backed state. No Tag click handlers are added in this phase. No Tag data, roster writes, persistence, calculations, Weapon selection, grid/layout, sizing, filters, Ability-title behavior, or lock behavior changes.
    Risk areas: Unified New View Ability Tag visual precedence only. No Weapon Tag gate changes, CSV data, Unit/Weapon calculations, Probable, lock/FIX, Boyz data, Cards, Waha, Edit, or persistence behavior changed.
  -->

'''
marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.139\n"
if text.count(marker) != 1:
    raise SystemExit("V31.139 change-note insertion marker missing")
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
    "/* V31.140 Ability Tag state outranks Weapon-selection muting. */",
    "badge.className='weapon-tag ability-tag-state '+(tagActive?'tag-state-on':'tag-state-off')+(tag&&tag.locked?' tag-state-locked':'');",
    ".unit-ability-tags .weapon-tag.ability-tag-state.tag-state-on{background:var(--btn)!important;color:var(--orange)!important;opacity:1!important}",
    ".unit-ability-tags .weapon-tag.ability-tag-state.tag-state-off{background:rgba(154,160,166,.5)!important;color:var(--muted)!important;opacity:1!important}",
    "const weaponSelected=selectedWeaponIndex===i;",
    "const displayActive=weaponSelected&&tagActive;",
    "el.classList.toggle('tag-state-on',Boolean(label)&&displayActive);",
    "el.classList.toggle('tag-state-off',Boolean(label)&&!displayActive);",
]:
    if expected not in final_view:
        raise SystemExit("V31.140 View acceptance failed: " + expected)

# Phase remains display-only: no New View Tag interaction is introduced.
for forbidden in [
    "toggleNewViewAbilityTag",
    "toggleNewViewWeaponTag",
    "onclick=\"toggleNewViewTag",
]:
    if forbidden in final_view:
        raise SystemExit("V31.140 acceptance failed: Tag click behavior was introduced")

for expected in [
    "<title>WH40k 11th V31.140</title>",
    "The current baseline is WH40k_11th_V31.140;",
    'const APP_VERSION = "31.140";',
    "version: 'V31.140',",
    "CHANGE NOTE - WH40k_11th_V31.140",
]:
    if expected not in text:
        raise SystemExit("V31.140 release acceptance failed: " + expected)

path.write_text(text, encoding="utf-8")
print("Built V31.140: Ability Tag On/Off state explicitly outranks Weapon-selection muting")
