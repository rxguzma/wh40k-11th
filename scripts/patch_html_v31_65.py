from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.64.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')

replacements = [
    ('<title>WH40k 11th V31.64</title>', '<title>WH40k 11th V31.65</title>'),
    ('The current baseline is WH40k_11th_V31.64;', 'The current baseline is WH40k_11th_V31.65;'),
    ('const APP_VERSION = "31.64";', 'const APP_VERSION = "31.65";'),
    ("version: 'V31.64',", "version: 'V31.65',"),
]
for old, new in replacements:
    if old not in text:
        raise SystemExit('version marker missing: ' + old)
    text = text.replace(old, new, 1)

frame_pattern = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
match = frame_pattern.search(text)
if not match:
    raise SystemExit('alternate View iframe not found')
np = html.unescape(match.group(2))

old = '''  const waha=grid.querySelector('.detail-waha');
  if(waha){
    const url=String(data&&data.waha||'').trim();
    waha.dataset.liveAvailable=url?'true':'false';
    waha.href=url||'#';
  }'''
new = '''  const waha=grid.querySelector('.detail-waha');
  if(waha){
    const rawUrl=String(data&&data.waha||'').trim();
    const isNazdreg=String(data&&data.name||'').trim().toLowerCase()==='nazdreg';
    const url=isNazdreg
      ? rawUrl.replace(/^https:\/\//i,'googlechromes://').replace(/^http:\/\//i,'googlechrome://')
      : rawUrl;
    waha.dataset.liveAvailable=rawUrl?'true':'false';
    waha.href=url||'#';
  }'''
if np.count(old) != 1:
    raise SystemExit(f'Waha wiring: expected 1 match, found {np.count(old)}')
np = np.replace(old, new, 1)

for required in [
    "const isNazdreg=String(data&&data.name||'').trim().toLowerCase()==='nazdreg';",
    "rawUrl.replace(/^https:\\/\\//i,'googlechromes://').replace(/^http:\\/\\//i,'googlechrome://')",
    "waha.dataset.liveAvailable=rawUrl?'true':'false';",
]:
    if required not in np:
        raise SystemExit('Nazdreg Chrome test check failed: ' + required)

np_srcdoc = html.escape(np, quote=True)
text = text[:match.start(2)] + np_srcdoc + text[match.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.65
    Scope: Test Chrome handoff for the alternate View Waha button on Nazdreg only. When the active unit name is exactly Nazdreg, its existing http/https Waha URL is converted to the Google Chrome iOS custom scheme. All other Waha links retain their existing URL and behavior.
    Risk areas: Alternate View Nazdreg Waha link only. No other unit links, View/Edit/Cards behavior, roster data, persistence, or combat logic changed.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.64\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

text = re.sub(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.60\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)

checks = [
    '<title>WH40k 11th V31.65</title>',
    'const APP_VERSION = "31.65";',
    "version: 'V31.65',",
    "googlechromes://",
    "googlechrome://",
    'CHANGE NOTE - WH40k_11th_V31.65',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('acceptance check failed: ' + ', '.join(missing))

out.write_text(text, encoding='utf-8')
print('Built V31.65: Nazdreg-only Waha Chrome handoff test')
