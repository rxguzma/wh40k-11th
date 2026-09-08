#!/usr/bin/env python3
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Remove hidden alias CSV and validator.
for rel in [
    "data/universal/Entity_Aliases.csv",
    "scripts/validate_aliases.py",
]:
    path = ROOT / rel
    if path.exists():
        path.unlink()
        print(f"removed {rel}")

# Remove Entity_Aliases.csv from CSV schema.
schema_path = ROOT / "data" / "CSV_SCHEMA.csv"
with schema_path.open(encoding="utf-8-sig", newline="") as handle:
    reader = csv.DictReader(handle)
    header = list(reader.fieldnames or [])
    rows = [row for row in reader if not (row.get("Scope") == "universal" and row.get("File") == "Entity_Aliases.csv")]
with schema_path.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
print("removed Entity_Aliases.csv schema rows")

# Remove alias compatibility from Entity Ops while retaining canonical-ID validation.
ops_path = ROOT / "scripts" / "entity_ops.py"
text = ops_path.read_text(encoding="utf-8")
text = re.sub(r'^\s*"Entity_Aliases\.csv": \[[^\n]+\],\n', '', text, flags=re.MULTILINE)
text = re.sub(r'^\s*self\.tables\[\(UNIVERSAL, "Entity_Aliases\.csv"\)\].*\n', '', text, flags=re.MULTILINE)
text = re.sub(
    r'\n\ndef resolve_entity_alias\(state, entity_type, army, value\):\n.*?\n\ndef validate_new_entity_id',
    '\n\ndef validate_new_entity_id',
    text,
    flags=re.DOTALL,
)
text = re.sub(
    r'\n\s*if mode != "add" and isinstance\(entity_id, str\):\n\s*entity_id = resolve_entity_alias\(state, entity, army, entity_id\)',
    '',
    text,
)
if "Entity_Aliases.csv" in text or "resolve_entity_alias" in text:
    raise SystemExit("alias compatibility references remain in entity_ops.py")
ops_path.write_text(text, encoding="utf-8")
print("removed Entity Ops alias resolution")
