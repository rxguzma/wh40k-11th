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


# Sequential release metadata only.
once('<title>WH40k 11th V31.115</title>', '<title>WH40k 11th V31.116</title>', 'title')
once('The current baseline is WH40k_11th_V31.115;', 'The current baseline is WH40k_11th_V31.116;', 'baseline')
once('const APP_VERSION = "31.115";', 'const APP_VERSION = "31.116";', 'APP_VERSION')
once("version: 'V31.115',", "version: 'V31.116',", 'quality version')

# V31.115 load failure: JavaScript forbids mixing && and ?? without explicit grouping.
# Fix only the malformed FIX-report value expression; no UI or behavior changes.
once(
    'value: String(item && item.value ?? ""),',
    'value: String((item && item.value) ?? ""),',
    'FIX report nullish-coalescing parse error'
)

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.116
    Scope: Repair the V31.115 startup failure caused by one invalid JavaScript expression in the visible FIX Report save bridge. The expression mixed logical AND and nullish coalescing without required parentheses, preventing the application script from parsing. V31.116 adds the required grouping only. No FIX Report layout, selection, persistence, Copy All/Done/Reset behavior, Boyz sub-unit presentation, roster data, CSV data, Version controls, Cards, Waha routing, or Probable behavior changes.
    Risk areas: FIX Report parent save bridge syntax only.
  -->

'''
marker = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.115\n'
if text.count(marker) != 1:
    raise SystemExit('V31.115 change-note insertion marker missing')
text = text.replace(marker, note + marker, 1)

# Keep only the five newest detailed V31 change notes.
notes = list(re.finditer(r'\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n', text, re.S))
for match in reversed(notes[5:]):
    text = text[:match.start()] + text[match.end():]

# Acceptance checks: malformed expression must be gone and repaired expression present.
if 'item && item.value ??' in text:
    raise SystemExit('V31.116 acceptance failed: unparenthesized && / ?? expression remains')
for expected in [
    '<title>WH40k 11th V31.116</title>',
    'The current baseline is WH40k_11th_V31.116;',
    'const APP_VERSION = "31.116";',
    "version: 'V31.116',",
    'value: String((item && item.value) ?? ""),',
    'CHANGE NOTE - WH40k_11th_V31.116',
]:
    if expected not in text:
        raise SystemExit('V31.116 acceptance failed: ' + expected)

path.write_text(text, encoding='utf-8')
print('Built V31.116: repaired V31.115 FIX Report JavaScript parse error')
