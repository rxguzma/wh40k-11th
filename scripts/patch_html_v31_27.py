from pathlib import Path
import re

source = Path("versions/WH40k_11th_V31.26.html")
path = Path("WH40k_11th.html")
text = source.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    text = text.replace(old, new, 1)


# Sequential release metadata.
replace_once('<title>WH40k 11th V31.26</title>', '<title>WH40k 11th V31.27</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.26;', 'The current baseline is WH40k_11th_V31.27;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.26";', 'const APP_VERSION = "31.27";', 'APP_VERSION')
replace_once("version: 'V31.26',", "version: 'V31.27',", 'InternalQuality version')

# Keep scoped tags in the title row. The title may wrap inside its own grid cell,
# but the tag group stays top-aligned beside it and never drops into a separate row.
old_css = '''    .ability-title-inline { display: flex; flex-wrap: wrap; align-items: center; gap: 4px; min-width: 0; }
    .ability-title-inline .ability-primary-name { display: inline; }
    .ability-title-scoped-tags { display: inline-flex; flex-wrap: wrap; align-items: center; gap: 3px; }
    .ability-title-scoped-tag { display: inline-flex; align-items: center; }
'''
new_css = '''    .ability-title-inline { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: start; column-gap: 6px; min-width: 0; width: 100%; }
    .ability-title-inline .ability-primary-name { display: block; min-width: 0; }
    .ability-title-scoped-tags { display: inline-flex; flex-wrap: nowrap; align-items: center; gap: 3px; white-space: nowrap; justify-self: end; }
    .ability-title-scoped-tag { display: inline-flex; align-items: center; }
    .ability-title-scoped-tag .weapon-ability-badge { font-size: 0.72em; line-height: 1.05; padding: 3px 7px; }
'''
replace_once(old_css, new_css, 'same-line Ability title Tag layout')

# Preserve the existing no-subtitle behavior explicitly. Range/Melee are filters only;
# they are not rendered as labels in Ability rows.
maintenance_anchor = '''    View-mode scoped Ability Tag layout invariant: non-Unit structured Tags render inline beside their Ability-like title, never in separate Melee/Range subtitle rows beneath the description. Canonical Range and Melee scoped title Tags follow the existing global View Range/Melee filter immediately; if a weapon category is hidden, Tags for that category are hidden too. Unit-level Tags remain on the Unit-level tag line.
'''
maintenance_replacement = '''    View-mode scoped Ability Tag layout invariant: non-Unit structured Tags render in the same title row beside their Ability-like title, never underneath the title and never in separate Melee/Range subtitle rows. The title can wrap within its own space, but the scoped Tag group remains top-aligned beside it. Canonical Range and Melee scoped title Tags follow the existing global View Range/Melee filter immediately; Range and Melee are controls only and must not be rendered as subtitles or labels in Ability rows. Unit-level Tags remain on the Unit-level tag line.
'''
replace_once(maintenance_anchor, maintenance_replacement, 'same-line/no-subtitle maintenance invariant')

# Add the new detailed release note and keep only the five newest detailed notes.
note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.26\n"
if note_marker not in text:
    raise SystemExit("release note insertion marker missing")
new_note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.27
    Scope: Keep scoped Ability-like Tags in the same title row as the Ability name instead of allowing the Tag group to wrap underneath. Preserve the compact V31.26 presentation with no Melee/Range subtitles; the existing top Range/Melee controls remain the only scope labels and continue to drive scoped Tag visibility.
    Risk areas: View Ability-table title/tag layout only. Tag activation, Range/Melee filtering, Unit-level Tag promotion, Weapon rules, Probable, and Edit Tag management remain unchanged.
  -->

'''
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.22\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f"old release note removal: expected 1 match, found {removed}")

checks = [
    '<title>WH40k 11th V31.27</title>',
    'const APP_VERSION = "31.27";',
    "version: 'V31.27',",
    'CHANGE NOTE - WH40k_11th_V31.27',
    'grid-template-columns: minmax(0, 1fr) auto',
    'flex-wrap: nowrap',
    'Range and Melee are controls only',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))
if 'ability-tag-scope-title' in text:
    raise SystemExit('Melee/Range subtitle renderer unexpectedly present')
if 'scopedSection("Melee"' in text or 'scopedSection("Range"' in text:
    raise SystemExit('Melee/Range scoped subtitle section unexpectedly present')

path.write_text(text, encoding="utf-8")
print("Built WH40k_11th.html as V31.27 with same-line scoped tags and no Range/Melee subtitles")
