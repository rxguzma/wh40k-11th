#!/usr/bin/env python3
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "data" / "CSV_SCHEMA.csv"
DATA_SCHEMA_PATH = ROOT / "scripts" / "data_schema.py"

OLD_HEADER = ["Scope", "File", "Column_Order", "Column_Name", "Required", "Notes"]
NEW_HEADER = ["Scope", "File", "Column_Order", "Column_Name", "Required", "Ownership", "Notes"]

GENERATED_COMPAT_FILES = {
    ("army", "Detachments.csv"),
    ("army", "Unit_Weapon_Options.csv"),
}

UNIT_GENERATED_COLUMNS = {
    "Ability_IDs",
    "Core_Ability_IDs",
    "Weapon_IDs",
    *{f"Points_Label_{index}" for index in range(1, 9)},
    *{f"Points_Cost_{index}" for index in range(1, 9)},
}

GENERATED_COLUMNS = {
    ("army", "Units.csv"): UNIT_GENERATED_COLUMNS,
    ("army", "Abilities.csv"): {"Tags"},
    ("army", "Enhancements.csv"): {"Tags"},
}


def fail(message):
    raise SystemExit(message)


def ownership_for(scope, file_name, column_name):
    key = (scope, file_name)
    if key in GENERATED_COMPAT_FILES:
        return "GENERATED_COMPAT"
    if column_name in GENERATED_COLUMNS.get(key, set()):
        return "GENERATED_COLUMN"
    return "AUTHORITATIVE"


def generated_note(scope, file_name, column_name, current):
    key = (scope, file_name)
    if key == ("army", "Units.csv"):
        if column_name == "Ability_IDs":
            return "Generated from Unit_Abilities.csv rows with Ability_Type=ABILITY; compatibility-only column."
        if column_name == "Core_Ability_IDs":
            return "Generated from Unit_Abilities.csv rows with Ability_Type=CORE_ABILITY; compatibility-only column."
        if column_name == "Weapon_IDs":
            return "Generated from Unit_Weapons.csv; compatibility-only column."
        if column_name.startswith("Points_Label_") or column_name.startswith("Points_Cost_"):
            return "Generated from Unit_Points.csv by point slot; compatibility-only column."
    if key == ("army", "Abilities.csv") and column_name == "Tags":
        return "Generated from Effects.csv Display_Tag values for this Ability_ID; presentation/legacy compatibility only."
    if key == ("army", "Enhancements.csv") and column_name == "Tags":
        return "Generated from Effects.csv Display_Tag values for this Enhancement_ID; presentation/legacy compatibility only."
    if key == ("army", "Detachments.csv"):
        return current or "Generated compatibility output from normalized detachment tables; do not author directly."
    if key == ("army", "Unit_Weapon_Options.csv"):
        return current or "Generated compatibility output from normalized Unit_Loadout_* tables; do not author directly."
    return current


def migrate_schema_csv():
    with SCHEMA_PATH.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames not in (OLD_HEADER, NEW_HEADER):
            fail(f"unexpected CSV_SCHEMA.csv header: {reader.fieldnames!r}")
        rows = list(reader)

    changed = reader.fieldnames != NEW_HEADER
    output = []
    for row in rows:
        scope = (row.get("Scope") or "").strip()
        file_name = (row.get("File") or "").strip()
        column_name = row.get("Column_Name") or ""
        expected_ownership = ownership_for(scope, file_name, column_name)
        current_ownership = (row.get("Ownership") or "").strip().upper()
        if current_ownership != expected_ownership:
            changed = True
        note = row.get("Notes") or ""
        next_note = generated_note(scope, file_name, column_name, note)
        if next_note != note:
            changed = True
        output.append({
            "Scope": row.get("Scope") or "",
            "File": row.get("File") or "",
            "Column_Order": row.get("Column_Order") or "",
            "Column_Name": column_name,
            "Required": row.get("Required") or "",
            "Ownership": expected_ownership,
            "Notes": next_note,
        })

    if changed:
        with SCHEMA_PATH.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=NEW_HEADER, lineterminator="\n")
            writer.writeheader()
            writer.writerows(output)
    return changed


def replace_once_or_confirm(text, old, new, label):
    if new in text:
        return text, False
    count = text.count(old)
    if count != 1:
        fail(f"could not patch {label}: expected one legacy block, found {count}")
    return text.replace(old, new, 1), True


def migrate_data_schema_py():
    text = DATA_SCHEMA_PATH.read_text(encoding="utf-8")
    changed = False

    replacements = [
        (
            'ALLOWED_UNIVERSAL_TYPES = {"CORE_STRATAGEM", "STRATAGEM"}\n',
            'ALLOWED_UNIVERSAL_TYPES = {"CORE_STRATAGEM", "STRATAGEM"}\nALLOWED_OWNERSHIP = {"AUTHORITATIVE", "GENERATED_COMPAT", "GENERATED_COLUMN"}\n',
            "ownership constants",
        ),
        (
            '    grouped = defaultdict(list)\n    required = defaultdict(set)\n',
            '    grouped = defaultdict(list)\n    required = defaultdict(set)\n    ownership_by_file = defaultdict(set)\n',
            "ownership map",
        ),
        (
            '        expected = ["Scope", "File", "Column_Order", "Column_Name", "Required", "Notes"]\n',
            '        expected = ["Scope", "File", "Column_Order", "Column_Name", "Required", "Ownership", "Notes"]\n',
            "schema header",
        ),
        (
            '            grouped[(scope, file_name)].append((order, column_name))\n            if (row.get("Required") or "").strip().upper() == "YES":\n                required[(scope, file_name)].add(column_name)\n',
            '            ownership = (row.get("Ownership") or "").strip().upper()\n            if ownership not in ALLOWED_OWNERSHIP:\n                fail(f"invalid Ownership {ownership!r} in schema row: {row!r}")\n            ownership_by_file[(scope, file_name)].add(ownership)\n            grouped[(scope, file_name)].append((order, column_name))\n            if (row.get("Required") or "").strip().upper() == "YES":\n                required[(scope, file_name)].add(column_name)\n',
            "ownership row validation",
        ),
        (
            '    schemas = {}\n',
            '    for key, ownerships in ownership_by_file.items():\n        if "GENERATED_COMPAT" in ownerships and ownerships != {"GENERATED_COMPAT"}:\n            fail(f"GENERATED_COMPAT must own every column for {key}: {sorted(ownerships)!r}")\n        if ownerships == {"GENERATED_COLUMN"}:\n            fail(f"file cannot contain only GENERATED_COLUMN ownership: {key}")\n\n    schemas = {}\n',
            "ownership file validation",
        ),
    ]

    for old, new, label in replacements:
        text, did_change = replace_once_or_confirm(text, old, new, label)
        changed = changed or did_change

    if changed:
        DATA_SCHEMA_PATH.write_text(text, encoding="utf-8")
    return changed


def main():
    schema_changed = migrate_schema_csv()
    code_changed = migrate_data_schema_py()
    print(
        "schema ownership migration:",
        f"CSV_SCHEMA={'updated' if schema_changed else 'current'},",
        f"data_schema.py={'updated' if code_changed else 'current'}",
    )


if __name__ == "__main__":
    main()
