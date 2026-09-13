from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.65.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')

replacements = [
    ('<title>WH40k 11th V31.65</title>', '<title>WH40k 11th V31.66</title>'),
    ('The current baseline is WH40k_11th_V31.65;', 'The current baseline is WH40k_11th_V31.66;'),
    ('const APP_VERSION = "31.65";', 'const APP_VERSION = "31.66";'),
    ("version: 'V31.65',", "version: 'V31.66',"),
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
    const rawUrl=String(data&&data.waha||'').trim();
    const isNazdreg=String(data&&data.name||'').trim().toLowerCase()==='nazdreg';
    const url=isNazdreg
      ? rawUrl.replace(/^https:\/\//i,'googlechromes://').replace(/^http:\/\//i,'googlechrome://')
      : rawUrl;
    waha.dataset.liveAvailable=rawUrl?'true':'false';
    waha.href=url||'#';
  }'''
new = '''  const waha=grid.querySelector('.detail-waha');
  if(waha){
    const url=String(data&&data.waha||'').trim();
    waha.dataset.liveAvailable=url?'true':'false';
    waha.href=url||'#';
  }'''
if np.count(old) != 1:
    raise SystemExit(f'Nazdreg Chrome special-case: expected 1 match, found {np.count(old)}')
np = np.replace(old, new, 1)

if "const isNazdreg=String(data&&data.name||'').trim().toLowerCase()==='nazdreg';" in np:
    raise SystemExit('Nazdreg HTML special-case still present')

np_srcdoc = html.escape(np, quote=True)
text = text[:match.start(2)] + np_srcdoc + text[match.end(2):]

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.66
    Scope: Revert the V31.65 Nazdreg-specific Chrome URL conversion. Alternate View Waha now uses the unit hyperlink exactly as supplied by data again, so Chrome-link testing can be performed through Unit_Profiles.csv only.
    Risk areas: Alternate View Waha URL assignment only. No roster data, other unit behavior, View/Edit/Cards behavior, persistence, or combat logic changed.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.65\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

text = re.sub(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.61\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)

checks = [
    '<title>WH40k 11th V31.66</title>',
    'const APP_VERSION = "31.66";',
    "version: 'V31.66',",
    "const url=String(data&&data.waha||'').trim();",
    'CHANGE NOTE - WH40k_11th_V31.66',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('acceptance check failed: ' + ', '.join(missing))

out.write_text(text, encoding='utf-8')
print('Built V31.66: Waha URL restored to data-driven behavior')
