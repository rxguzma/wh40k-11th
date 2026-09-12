from pathlib import Path
import csv
import io

ROOT = Path(__file__).resolve().parents[1]
schema_path = ROOT / 'data' / 'CSV_SCHEMA.csv'
text = schema_path.read_text(encoding='utf-8')

rows = [
    ['army', 'Detachment_Definitions.csv', '14', 'Required_Keywords', 'NO', 'AUTHORITATIVE', 'All listed Unit keywords are required for this rule.'],
    ['army', 'Detachment_Definitions.csv', '15', 'Any_Keywords', 'NO', 'AUTHORITATIVE', 'At least one listed Unit keyword is required when populated.'],
    ['army', 'Detachment_Definitions.csv', '16', 'Excluded_Keywords', 'NO', 'AUTHORITATIVE', 'Any listed Unit keyword makes this rule ineligible.'],
    ['army', 'Enhancements.csv', '11', 'Required_Keywords', 'NO', 'AUTHORITATIVE', 'All listed Unit keywords are required for this Enhancement.'],
    ['army', 'Enhancements.csv', '12', 'Any_Keywords', 'NO', 'AUTHORITATIVE', 'At least one listed Unit keyword is required when populated.'],
    ['army', 'Enhancements.csv', '13', 'Excluded_Keywords', 'NO', 'AUTHORITATIVE', 'Any listed Unit keyword makes this Enhancement ineligible.'],
    ['army', 'Army_Rules.csv', '9', 'Required_Keywords', 'NO', 'AUTHORITATIVE', 'All listed Unit keywords are required for this rule.'],
    ['army', 'Army_Rules.csv', '10', 'Any_Keywords', 'NO', 'AUTHORITATIVE', 'At least one listed Unit keyword is required when populated.'],
    ['army', 'Army_Rules.csv', '11', 'Excluded_Keywords', 'NO', 'AUTHORITATIVE', 'Any listed Unit keyword makes this rule ineligible.'],
    ['army', 'Stratagems.csv', '10', 'Required_Keywords', 'NO', 'AUTHORITATIVE', 'All listed Unit keywords are required for this Stratagem.'],
    ['army', 'Stratagems.csv', '11', 'Any_Keywords', 'NO', 'AUTHORITATIVE', 'At least one listed Unit keyword is required when populated.'],
    ['army', 'Stratagems.csv', '12', 'Excluded_Keywords', 'NO', 'AUTHORITATIVE', 'Any listed Unit keyword makes this Stratagem ineligible.'],
]

existing = set()
with schema_path.open(encoding='utf-8-sig', newline='') as handle:
    for row in csv.DictReader(handle):
        existing.add(((row.get('Scope') or '').strip(), (row.get('File') or '').strip(), (row.get('Column_Name') or '').strip()))

missing = [row for row in rows if (row[0], row[1], row[3]) not in existing]
if missing:
    buf = io.StringIO()
    csv.writer(buf, lineterminator='\n').writerows(missing)
    if not text.endswith('\n'):
        text += '\n'
    schema_path.write_text(text + buf.getvalue(), encoding='utf-8')

print(f'eligibility schema rows added: {len(missing)}')
