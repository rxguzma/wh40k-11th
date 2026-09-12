from pathlib import Path
import re

source = Path("versions/WH40k_11th_V31.22.html")
path = Path("WH40k_11th.html")
text = source.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    text = text.replace(old, new, 1)


# Sequential release metadata.
replace_once('<title>WH40k 11th V31.22</title>', '<title>WH40k 11th V31.23</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.22;', 'The current baseline is WH40k_11th_V31.23;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.22";', 'const APP_VERSION = "31.23";', 'APP_VERSION')
replace_once("version: 'V31.22',", "version: 'V31.23',", 'InternalQuality version')

# View-mode Ability ordering: rows assigned order 8 or 9 are management/composition
# rows and should not render at all in View. Edit mode must still render them so the
# user can inspect, edit, and change their order.
old_descriptor_render = '''      const descriptors = buildUnitAbilityRowDescriptors(abilities, entry, roster, editKey, isEditing);
      const rows = descriptors.map((descriptor, rowIndex) => {'''
new_descriptor_render = '''      const descriptors = buildUnitAbilityRowDescriptors(abilities, entry, roster, editKey, isEditing);
      const visibleDescriptors = appEditMode
        ? descriptors
        : descriptors.filter(descriptor => ![8, 9].includes(Number(descriptor.order)));
      const rows = visibleDescriptors.map((descriptor, rowIndex) => {'''
replace_once(old_descriptor_render, new_descriptor_render, 'View order 8/9 visibility filter')

# Preserve this as an explicit regression-sensitive View/Edit contract.
maintenance_anchor = '''    View-mode scoped Tag invariant: structured Ability-like Tags with canonical Melee or Range scope render under separate Melee and Range subtitles. When an active source Tag defines a reroll for a Weapon scope, the applicable effective Weapon profiles also display that reroll as a derived locked rule; the source Tag remains the only control for enabling or disabling it.
'''
maintenance_replacement = maintenance_anchor + '''
    View-mode Ability ordering invariant: Ability-table items whose effective order is 8 or 9 do not render at all in View mode. Edit mode continues to render them, including their order controls, so they remain manageable and can be moved back into visible orders 0-7.
'''
replace_once(maintenance_anchor, maintenance_replacement, 'View order maintenance invariant')

# Add the new detailed release note and keep only the five newest detailed notes.
note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.22\n"
if note_marker not in text:
    raise SystemExit("release note insertion marker missing")
new_note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.23
    Scope: Hide Ability-table items with effective order 8 or 9 from View mode entirely. Edit mode continues to show those items and their order controls so they can still be managed or moved back to orders 0-7.
    Risk areas: View-mode Ability row visibility only. Ability ordering data, Edit-mode rows, Tag behavior, Weapon profiles, and Probable remain unchanged.
  -->

'''
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.18\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f"old release note removal: expected 1 match, found {removed}")

checks = [
    '<title>WH40k 11th V31.23</title>',
    'const APP_VERSION = "31.23";',
    "version: 'V31.23',",
    'CHANGE NOTE - WH40k_11th_V31.23',
    'const visibleDescriptors = appEditMode',
    'descriptors.filter(descriptor => ![8, 9].includes(Number(descriptor.order)))',
    'View-mode Ability ordering invariant:',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))
if old_descriptor_render in text:
    raise SystemExit('View still renders all Ability order descriptors')

path.write_text(text, encoding="utf-8")
print("Built WH40k_11th.html as V31.23 with View orders 8/9 hidden")
