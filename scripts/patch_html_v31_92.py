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


# Sequential release metadata.
once('<title>WH40k 11th V31.91</title>', '<title>WH40k 11th V31.92</title>', 'title')
once('The current baseline is WH40k_11th_V31.91;', 'The current baseline is WH40k_11th_V31.92;', 'baseline')
once('const APP_VERSION = "31.91";', 'const APP_VERSION = "31.92";', 'APP_VERSION')
once("version: 'V31.91',", "version: 'V31.92',", 'quality version')

view_pat = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
vm = view_pat.search(text)
if not vm:
    raise SystemExit('New View iframe missing')
view_np = html.unescape(vm.group(2))

# Promote the existing visual lock state into the New View processing lock.
# activePageMode keeps the lock scoped to VIEW only; the unified EDIT state
# remains live and unchanged.
old_lock_state = "let newViewHeaderLocked=false;"
new_lock_state = "let newViewHeaderLocked=false;\nlet activePageMode='view';\nfunction newViewProcessingLocked(){return Boolean(newViewHeaderLocked&&activePageMode==='view')}"
if view_np.count(old_lock_state) != 1:
    raise SystemExit(f'New View lock state: expected 1 match, found {view_np.count(old_lock_state)}')
view_np = view_np.replace(old_lock_state, new_lock_state, 1)

# Direct refresh entry points must return before parent/model access while the
# New View lock is on. This protects parent-triggered refreshes as well as the
# normal post-render refresh path.
header_sig = "function refreshNewViewTitleFromLegacy(){"
if view_np.count(header_sig) != 1:
    raise SystemExit(f'New View header refresh: expected 1 match, found {view_np.count(header_sig)}')
view_np = view_np.replace(header_sig, header_sig + "if(newViewProcessingLocked())return false;", 1)

roster_sig = "function refreshAlternateViewUnitsFromParent(){"
if view_np.count(roster_sig) != 1:
    raise SystemExit(f'New View roster refresh: expected 1 match, found {view_np.count(roster_sig)}')
view_np = view_np.replace(roster_sig, roster_sig + "if(newViewProcessingLocked())return false;", 1)

# One central New View refresh gate. In the unlocked state it performs the same
# two refreshes as before, in the same order. In the locked state it exits before
# either refresh can reach the parent/model layer.
render_marker = "function renderPage(p){"
if view_np.count(render_marker) != 1:
    raise SystemExit(f'New View render marker: expected 1 match, found {view_np.count(render_marker)}')
refresh_gate = "function refreshNewView(){if(newViewProcessingLocked())return false;refreshNewViewTitleFromLegacy();return refreshAlternateViewUnitsFromParent()}\n"
view_np = view_np.replace(render_marker, refresh_gate + "function renderPage(p){activePageMode=p;", 1)

old_post = "if(p==='view'){requestAnimationFrame(refreshNewViewTitleFromLegacy);requestAnimationFrame(refreshAlternateViewUnitsFromParent)}"
new_post = "if(p==='view'){requestAnimationFrame(refreshNewView)}"
if view_np.count(old_post) != 1:
    raise SystemExit(f'New View post-render refresh: expected 1 match, found {view_np.count(old_post)}')
view_np = view_np.replace(old_post, new_post, 1)

# Write the modified New View document back.
view_srcdoc = html.escape(view_np, quote=True)
text = text[:vm.start(2)] + view_srcdoc + text[vm.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.92
    Scope: Connect the existing New View lock button to the first processing-freeze gate. The existing newViewHeaderLocked state is now the actual New View lock state. While VIEW is locked, both direct New View header refresh and roster refresh entry points return before parent/model access, and the normal VIEW post-render path now funnels through one refreshNewView gate. Unlocked VIEW behavior remains the same two refreshes in the same order. The unified EDIT state remains live and unchanged. This pass does not add the frozen snapshot yet and does not change Unit/filter interaction behavior.
    Risk areas: New View refresh entry points and VIEW/EDIT mode tracking only. Existing lock icon/placement, New View UI layout, unified Edit rows, Old Edit, Cards, persistence, CSV data, Waha routing, and Probable remain unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.91\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

# Retain only the five newest V31 detailed notes.
notes = list(re.finditer(r'\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n', text, re.S))
for match in reversed(notes[5:]):
    text = text[:match.start()] + text[match.end():]

# Final acceptance checks.
vm = view_pat.search(text)
if not vm:
    raise SystemExit('New View iframe missing after writeback')
final_view = html.unescape(vm.group(2))
required_view = [
    "let newViewHeaderLocked=false;",
    "let activePageMode='view';",
    "function newViewProcessingLocked(){return Boolean(newViewHeaderLocked&&activePageMode==='view')}",
    "function refreshNewView(){if(newViewProcessingLocked())return false;refreshNewViewTitleFromLegacy();return refreshAlternateViewUnitsFromParent()}",
    "function renderPage(p){activePageMode=p;",
    "if(p==='view'){requestAnimationFrame(refreshNewView)}",
    "newViewHeaderLocked=!newViewHeaderLocked;syncNewViewLockButton(lb)",
]
for value in required_view:
    if value not in final_view:
        raise SystemExit('V31.92 New View acceptance failed: ' + value)

if final_view.count('if(newViewProcessingLocked())return false;') < 3:
    raise SystemExit('V31.92 processing gate missing from one or more refresh entry points')

# Ensure the old two-RAF VIEW refresh path is gone, while EDIT keeps its own
# existing live refresh behavior.
if old_post in final_view:
    raise SystemExit('V31.92 old VIEW refresh path remains')
if "if(p==='edit'){requestAnimationFrame(refreshNewViewTitleFromLegacy);requestAnimationFrame(refreshUnifiedEditRows)}" not in final_view:
    raise SystemExit('V31.92 unified EDIT refresh path changed unexpectedly')

required_outer = [
    '<title>WH40k 11th V31.92</title>',
    'const APP_VERSION = "31.92";',
    "version: 'V31.92',",
    'CHANGE NOTE - WH40k_11th_V31.92',
]
for value in required_outer:
    if value not in text:
        raise SystemExit('V31.92 acceptance failed: ' + value)

path.write_text(text, encoding='utf-8')
print('Built V31.92: existing New View lock now gates header/roster refresh processing')
