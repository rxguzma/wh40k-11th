#!/usr/bin/env python3
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMIES = ("marines", "orks", "nids")

# Remove hidden compatibility files and old canonical loadout-alias data.
for rel in [
    "data/universal/Entity_Aliases.csv",
    "scripts/validate_aliases.py",
    *[f"data/{army}/Loadout_Legacy_Units.csv" for army in ARMIES],
]:
    path = ROOT / rel
    if path.exists():
        path.unlink()
        print(f"removed {rel}")

# Remove obsolete files from CSV schema. Keep Unit_Loadout_Legacy_Units.csv as an empty
# generated compatibility stub because the current HTML still requests that filename.
schema_path = ROOT / "data" / "CSV_SCHEMA.csv"
with schema_path.open(encoding="utf-8-sig", newline="") as handle:
    reader = csv.DictReader(handle)
    header = list(reader.fieldnames or [])
    rows = [
        row for row in reader
        if not (
            (row.get("Scope") == "universal" and row.get("File") == "Entity_Aliases.csv")
            or (row.get("Scope") == "army" and row.get("File") == "Loadout_Legacy_Units.csv")
        )
    ]
with schema_path.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
print("removed legacy alias schema rows")

# No-New validator no longer needs hidden-alias exceptions.
validator_path = ROOT / "scripts" / "validate_no_new_names.py"
validator_path.write_text(r'''#!/usr/bin/env python3
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEW_ID_RE = re.compile(r"(?:^NEW(?:_|$)|_NEW(?:_|$)|\(New\))", re.IGNORECASE)
NEW_NAME_RE = re.compile(r"\(\s*New\s*\)", re.IGNORECASE)


def fail(message):
    raise SystemExit(message)


def main():
    issues = []
    for path in sorted((ROOT / "data").rglob("*.csv")):
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for line_no, row in enumerate(reader, start=2):
                for column, value in row.items():
                    text = (value or "").strip()
                    if not text:
                        continue
                    is_id = column == "Item_ID" or column.endswith("_ID") or column in {"Ability_ID", "Weapon_ID", "Unit_ID"}
                    is_name = column.endswith("Name") or column.endswith("_Name") or column in {"Ability Name", "Weapon Name", "Unit Name"}
                    if is_id and NEW_ID_RE.search(text):
                        issues.append(f"{path.relative_to(ROOT)}:{line_no}:{column}={text}")
                    if is_name and NEW_NAME_RE.search(text):
                        issues.append(f"{path.relative_to(ROOT)}:{line_no}:{column}={text}")
    if issues:
        fail("New naming remains in repository data:\n" + "\n".join(issues))
    print("New-name audit: OK — no '(New)' / NEW_* identifiers")


if __name__ == "__main__":
    main()
''', encoding="utf-8")
print("simplified no-New validator")

# Remove alias resolution and legacy-unit loadout support from Entity Ops.
ops_path = ROOT / "scripts" / "entity_ops.py"
text = ops_path.read_text(encoding="utf-8")
text = re.sub(r'^\s*"Entity_Aliases\.csv": \[[^\n]+\],\n', '', text, flags=re.MULTILINE)
text = re.sub(r'^\s*"Loadout_Legacy_Units\.csv": \[[^\n]+\],\n', '', text, flags=re.MULTILINE)
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
text = re.sub(
    r'\n    if "legacy_units" in payload:\n.*?(?=\ndef add_unit\()',
    '\n',
    text,
    flags=re.DOTALL,
)
# Remove canonical legacy-unit table from State/delete cascades.
text = re.sub(r'\s*"Loadout_Legacy_Units\.csv",\n', '\n', text)
text = re.sub(r',\s*"Loadout_Legacy_Units\.csv"', '', text)
text = re.sub(r'"Loadout_Legacy_Units\.csv",\s*', '', text)
for forbidden in ("Entity_Aliases.csv", "resolve_entity_alias", "Loadout_Legacy_Units.csv", '"legacy_units"'):
    if forbidden in text:
        raise SystemExit(f"legacy reference remains in entity_ops.py: {forbidden}")
ops_path.write_text(text, encoding="utf-8")
print("removed Entity Ops legacy compatibility")

# Remove legacy_units from the LLM-facing JSON contract.
entity_schema_path = ROOT / "schemas" / "entity-ops.schema.json"
schema = json.loads(entity_schema_path.read_text(encoding="utf-8"))
defs = schema.get("$defs", {})
defs.pop("legacyUnit", None)
for name in ("loadoutAdd", "nestedLoadoutAdd", "loadoutChange"):
    defs.get(name, {}).get("properties", {}).pop("legacy_units", None)
entity_schema_path.write_text(json.dumps(schema, separators=(",", ":")) + "\n", encoding="utf-8")
print("removed legacy_units from Entity Ops schema")

# Canonical loadout generator: remove Loadout_Legacy_Units.csv input and always emit an
# empty Unit_Loadout_Legacy_Units.csv stub for the unchanged HTML contract.
split_path = ROOT / "scripts" / "split_loadouts_v1.py"
s = split_path.read_text(encoding="utf-8")
s = re.sub(r'^CANON_LEGACY_UNITS_HEADER = \[[^\n]+\]\n', '', s, flags=re.MULTILINE)
s = s.replace('    legacy_units = read_dicts(directory / "Loadout_Legacy_Units.csv", CANON_LEGACY_UNITS_HEADER)\n', '')
s = s.replace('    return options, weapons, abilities, points, compatibility, legacy_units\n', '    return options, weapons, abilities, points, compatibility\n')
s = s.replace('    options, weapons, abilities, points, compatibility, legacy_units = tables\n', '    options, weapons, abilities, points, compatibility = tables\n')
s = s.replace('        ("Loadout_Legacy_Units.csv", legacy_units),\n', '')
s = re.sub(
    r'    compat_legacy_units = \[\n.*?\n    \]\n\n    write_csv\(directory / "Unit_Loadout_Options\.csv"',
    '    compat_legacy_units = []\n\n    write_csv(directory / "Unit_Loadout_Options.csv"',
    s,
    flags=re.DOTALL,
)
s = s.replace('    options, weapons, abilities, points, compatibility, legacy_units = compat_tables\n', '    options, weapons, abilities, points, compatibility, _ = compat_tables\n')
s = s.replace('    legacy_links = defaultdict(list)\n', '')
s = re.sub(
    r'\n    for source_index, row in enumerate\(legacy_units\):\n        key = .*?\n        legacy_links\[key\]\.append\(.*?\n',
    '\n',
    s,
    flags=re.DOTALL,
)
s = re.sub(r'        aliases = ", "\.join\(item\[2\] for item in sorted\(legacy_links\[key\]\)\)\n', '        aliases = ""\n', s)
s = s.replace(
    '        f"{len(compatibility)} compatibility rows, {len(legacy_units)} legacy aliases)"\n',
    '        f"{len(compatibility)} compatibility rows)"\n',
)
for forbidden in ("CANON_LEGACY_UNITS_HEADER", 'directory / "Loadout_Legacy_Units.csv"', "legacy_links"):
    if forbidden in s:
        raise SystemExit(f"legacy reference remains in split_loadouts_v1.py: {forbidden}")
split_path.write_text(s, encoding="utf-8")
print("removed canonical legacy-unit loadout generation")

# Loadout validator now expects five canonical tables and an empty sixth compatibility stub.
validate_path = ROOT / "scripts" / "validate_loadouts.py"
v = validate_path.read_text(encoding="utf-8")
v = re.sub(r'^\s*"Loadout_Legacy_Units\.csv": \[[^\n]+\],\n', '', v, flags=re.MULTILINE)
v = re.sub(
    r'\n        for index, legacy_unit_id in enumerate\(split_ids\(row\.get\("Legacy_Unit_IDs"\)\), start=1\):\n            legacy_units\.append\(\(unit_id, group_id, option_id, legacy_unit_id, str\(index\)\)\)\n',
    '\n',
    v,
)
v = v.replace('    options, weapons, abilities, points, compatibility, legacy_units = canonical\n', '    options, weapons, abilities, points, compatibility = canonical\n')
v = v.replace('    options, weapons, abilities, points, compatibility, legacy_units = canonical\n', '    options, weapons, abilities, points, compatibility = canonical\n')
v = v.replace(
    '            (*parent(row), row["Legacy_Unit_ID"], row["Sort_Order"])\n            for row in legacy_units\n        ],\n',
    '        [],\n',
)
v = v.replace(', "Loadout_Legacy_Units.csv"', '')
v = v.replace(
    '        f"{len(abilities)} abilities, {len(points)} points, {len(compatibility)} compatibility rows, "\n        f"{len(legacy_units)} legacy aliases"\n',
    '        f"{len(abilities)} abilities, {len(points)} points, {len(compatibility)} compatibility rows"\n',
)
if '"Loadout_Legacy_Units.csv":' in v or 'row["Legacy_Unit_ID"]' in v:
    raise SystemExit("canonical legacy reference remains in validate_loadouts.py")
validate_path.write_text(v, encoding="utf-8")
print("removed canonical legacy-unit loadout validation")

print("legacy compatibility cleanup prepared")
