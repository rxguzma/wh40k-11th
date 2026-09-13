from pathlib import Path
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
once('<title>WH40k 11th V31.88</title>', '<title>WH40k 11th V31.89</title>', 'title')
once('The current baseline is WH40k_11th_V31.88;', 'The current baseline is WH40k_11th_V31.89;', 'baseline')
once('const APP_VERSION = "31.88";', 'const APP_VERSION = "31.89";', 'APP_VERSION')
once("version: 'V31.88',", "version: 'V31.89',", 'quality version')

# V31.88 correctly renamed the New View title refresh function after removing
# New Edit from the data path, but the parent show-New-View callback still used
# the old function name. Units refreshed because their callback name did not
# change; the title/header stayed stale/blank. Point the parent callback at the
# direct legacy/model title refresh function.
old_refresh = '''        if (npWindow && typeof npWindow.refreshNewViewTitleFromNewEdit === "function") npWindow.refreshNewViewTitleFromNewEdit();'''
new_refresh = '''        if (npWindow && typeof npWindow.refreshNewViewTitleFromLegacy === "function") npWindow.refreshNewViewTitleFromLegacy();'''
once(old_refresh, new_refresh, 'New View title refresh callback')

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.89
    Scope: Fix the remaining New View title refresh wiring after V31.88 removed New Edit from the data path. The parent screen-opening callback now calls refreshNewViewTitleFromLegacy instead of the retired refreshNewViewTitleFromNewEdit name, so roster name, Detachments, Disposition, and points refresh from getAlternateViewHeaderData whenever New View is opened. Unit/Weapon wiring and Old Edit routing are unchanged.
    Risk areas: New View title/header refresh callback only.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.88\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

# Retain only the five newest V31 change-note blocks.
notes = list(re.finditer(r'\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n', text, re.S))
for match in reversed(notes[5:]):
    text = text[:match.start()] + text[match.end():]

required = [
    '<title>WH40k 11th V31.89</title>',
    'const APP_VERSION = "31.89";',
    "version: 'V31.89',",
    'typeof npWindow.refreshNewViewTitleFromLegacy === "function"',
    'npWindow.refreshNewViewTitleFromLegacy();',
    'CHANGE NOTE - WH40k_11th_V31.89',
]
for value in required:
    if value not in text:
        raise SystemExit(f'V31.89 acceptance failed: {value}')

# The parent callback must no longer reference the retired New Edit-named title refresh.
if old_refresh in text:
    raise SystemExit('retired New View title callback remains')

path.write_text(text, encoding='utf-8')
print('Built V31.89: fixed direct New View title refresh callback')
