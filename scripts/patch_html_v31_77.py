from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.76.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


once('<title>WH40k 11th V31.76</title>', '<title>WH40k 11th V31.77</title>', 'title')
once('The current baseline is WH40k_11th_V31.76;', 'The current baseline is WH40k_11th_V31.77;', 'baseline')
once('const APP_VERSION = "31.76";', 'const APP_VERSION = "31.77";', 'APP_VERSION')
once("version: 'V31.76',", "version: 'V31.77',", 'quality version')

edit_pat = re.compile(r'(<iframe id="npEditFrame" class="np-view-frame" title="New Edit" srcdoc=")(.*?)("></iframe>)', re.S)
em = edit_pat.search(text)
if not em:
    raise SystemExit('New Edit iframe missing')
edit_np = html.unescape(em.group(2))

# New Edit no longer needs VP in its staged header contract.
old_header_record = '''    disposition:String(data.disposition||''),
    points:Number(data.points)||0,
    vp:Number(data.vp)||0,
    summaryRest:String(data.summaryRest||'')'''
new_header_record = '''    disposition:String(data.disposition||''),
    points:Number(data.points)||0,
    summaryRest:String(data.summaryRest||'')'''
if edit_np.count(old_header_record) != 1:
    raise SystemExit(f'New Edit header record: expected 1 match, found {edit_np.count(old_header_record)}')
edit_np = edit_np.replace(old_header_record, new_header_record, 1)

text = text[:em.start(2)] + html.escape(edit_np, quote=True) + text[em.end(2):]

# Temporary Old Edit/model -> New Edit header bridge now supplies disposition + points only.
old_parent = '''      const points = getRosterPoints(roster);
      const vp = getCardsTotalVpForRoster(roster);
      return {
        rosterName: String(roster.name || "").trim() || "Army",
        detachments: detachmentNames.join(" - "),
        disposition: selectedDisposition || (detachmentNames.length ? "Disposition?" : ""),
        points,
        vp,
        summaryRest: `- ${points} pts - ${vp} VPs`
      };'''
new_parent = '''      const points = getRosterPoints(roster);
      return {
        rosterName: String(roster.name || "").trim() || "Army",
        detachments: detachmentNames.join(" - "),
        disposition: selectedDisposition || (detachmentNames.length ? "Disposition?" : ""),
        points,
        summaryRest: `- ${points} pts`
      };'''
if text.count(old_parent) != 1:
    raise SystemExit(f'header bridge VP block: expected 1 match, found {text.count(old_parent)}')
text = text.replace(old_parent, new_parent, 1)

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.77
    Scope: Remove VP total from the staged New Edit title contract. New Edit title line three now contains only active Disposition and roster points, for example “Priority Assets - 1995 pts”. The temporary Old Edit/model -> New Edit bridge no longer calculates or passes VP for this title. New View remains intentionally unlinked from New Edit and otherwise unchanged.
    Risk areas: New Edit staged title data only. Unit data, Weapons, Old Edit behavior, New View behavior, Cards, persistence, CSV data, Waha routing, and Probable are unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.76\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.72\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

# Acceptance checks.
em = edit_pat.search(text)
if not em:
    raise SystemExit('New Edit iframe missing after writeback')
final_edit = html.unescape(em.group(2))
for forbidden in [
    'vp:Number(data.vp)||0,',
    'const vp = getCardsTotalVpForRoster(roster);',
    'summaryRest: `- ${points} pts - ${vp} VPs`',
]:
    if forbidden in text or forbidden in final_edit:
        raise SystemExit('VP title dependency remains: ' + forbidden)
for required in [
    '<title>WH40k 11th V31.77</title>',
    'const APP_VERSION = "31.77";',
    "version: 'V31.77',",
    'summaryRest: `- ${points} pts`',
    'CHANGE NOTE - WH40k_11th_V31.77',
]:
    if required not in text:
        raise SystemExit('acceptance check failed: ' + required)

out.write_text(text, encoding='utf-8')
print('Built V31.77: removed VP total from staged New Edit title')
