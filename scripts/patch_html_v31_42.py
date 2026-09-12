from pathlib import Path
import re

source = Path("versions/WH40k_11th_V31.41.html")
path = Path("WH40k_11th.html")
text = source.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    text = text.replace(old, new, 1)


replace_once('<title>WH40k 11th V31.41</title>', '<title>WH40k 11th V31.42</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.41;', 'The current baseline is WH40k_11th_V31.42;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.41";', 'const APP_VERSION = "31.42";', 'APP_VERSION')
replace_once("version: 'V31.41',", "version: 'V31.42',", 'InternalQuality version')

replace_once(
    '<button id="newPageModeToggle" class="secondary app-mode-button new-page-mode-toggle" aria-pressed="false" onclick="event.stopPropagation(); UI.selectAppMode(\'newpage\')">New Page</button>',
    '<button id="newPageModeToggle" class="secondary app-mode-button new-page-mode-toggle" aria-pressed="false" onclick="event.stopPropagation(); window.location.href=\'Np1.01.html\'">New Page</button>',
    'New Page local launcher',
)

# The NP surface now lives in its own file. Remove the old embedded screen only;
# leave unrelated title-control geometry untouched.
pattern = re.compile(
    r'\n  <div id="newPageScreen" class="screen new-page-screen" aria-label="New page">.*?</div>\n\n  <div id="rosterScreen" class="screen active">',
    re.S,
)
text, count = pattern.subn('\n  <div id="rosterScreen" class="screen active">', text, count=1)
if count != 1:
    raise SystemExit(f'embedded New Page removal: expected 1 match, found {count}')

note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.41\n"
if note_marker not in text:
    raise SystemExit('release note insertion marker missing')
new_note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.42
    Scope: New Page is now a separate local HTML surface. The existing New Page title button opens sibling file Np1.01.html, which acts as the stable local launcher and owns its own GitHub Update/Download flow. The obsolete embedded New Page screen was removed from the main HTML.
    Risk areas: New Page navigation only. Existing View, Edit, Cards, roster data, and combat behavior are unchanged.
  -->

'''
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.38\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f'old release note removal: expected 1 match, found {removed}')

checks = [
    '<title>WH40k 11th V31.42</title>',
    'const APP_VERSION = "31.42";',
    "version: 'V31.42',",
    'CHANGE NOTE - WH40k_11th_V31.42',
    "window.location.href='Np1.01.html'",
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))
if 'id="newPageScreen"' in text:
    raise SystemExit('embedded New Page screen still present')

path.write_text(text, encoding='utf-8')
print('Built WH40k_11th.html as V31.42 with local Np1.01 launcher')
