#!/usr/bin/env python3
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "data" / "CSV_SCHEMA.csv"
ARMIES = ("marines", "orks", "nids")
TRUE_VALUES = {"true", "1", "yes", "y"}
ALLOWED_DETACHMENT_TYPES = {"ARMY_RULE", "DETACHMENT_RULE", "ENHANCEMENT", "STRATAGEM"}
ALLOWED_UNIVERSAL_TYPES = {"CORE_STRATAGEM", "STRATAGEM"}


def fail(message):
    raise SystemExit(message)


def load_schema():
    if not SCHEMA_PATH.is_file():
        fail(f"missing schema: {SCHEMA_PATH}")
    grouped = defaultdict(list)
    required = defaultdict(set)
    with SCHEMA_PATH.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        expected = ["Scope", "File", "Column_Order", "Column_Name", "Required", "Notes"]
        if reader.fieldnames != expected:
            fail(f"CSV_SCHEMA.csv header must be exactly {expected!r}")
        for row in reader:
            scope = (row.get("Scope") or "").strip()
            file_name = (row.get("File") or "").strip()
            column_name = row.get("Column_Name") or ""
            try:
                order = int((row.get("Column_Order") or "").strip())
            except ValueError:
                fail(f"bad Column_Order in schema: {row!r}")
            if not scope or not file_name or not column_name:
                fail(f"incomplete schema row: {row!r}")
            grouped[(scope, file_name)].append((order, column_name))
            if (row.get("Required") or "").strip().upper() == "YES":
                required[(scope, file_name)].add(column_name)
    schemas = {}
    for key, entries in grouped.items():
        entries.sort()
        orders = [order for order, _ in entries]
        if orders != list(range(1, len(entries) + 1)):
            fail(f"non-contiguous schema order for {key}: {orders}")
        headers = [column for _, column in entries]
        if len(headers) != len(set(headers)):
            fail(f"duplicate schema column for {key}")
        schemas[key] = headers
    return schemas, required


def specs(schemas):
    result = []
    army_files = sorted(file_name for scope, file_name in schemas if scope == "army")
    universal_files = sorted(file_name for scope, file_name in schemas if scope == "universal")
    for army in ARMIES:
        for file_name in army_files:
            result.append(("army", army, file_name, ROOT / "data" / army / file_name))
    for file_name in universal_files:
        result.append(("universal", "universal", file_name, ROOT / "data" / "universal" / file_name))
    return result


def read_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.reader(handle))


def write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle, lineterminator="\n").writerows(rows)


def normalize():
    schemas, _ = load_schema()
    changed = []
    for scope, owner, file_name, path in specs(schemas):
        canonical = schemas[(scope, file_name)]
        if not path.exists():
            if scope == "army" and file_name == "Unit_Weapon_Options.csv":
                write_rows(path, [canonical])
                changed.append(str(path.relative_to(ROOT)))
                continue
            fail(f"missing required CSV: {path.relative_to(ROOT)}")
        rows = read_rows(path)
        if not rows:
            fail(f"empty CSV: {path.relative_to(ROOT)}")
        header = rows[0]
        if len(header) != len(set(header)):
            fail(f"duplicate header in {path.relative_to(ROOT)}: {header!r}")
        unknown = [column for column in header if column not in canonical]
        if unknown:
            fail(f"unknown columns in {path.relative_to(ROOT)}: {unknown!r}")
        index = {column: i for i, column in enumerate(header)}
        new_rows = [canonical]
        row_width_changed = False
        for line_no, row in enumerate(rows[1:], start=2):
            if not row or not any(cell != "" for cell in row):
                continue
            if len(row) > len(header):
                extras = row[len(header):]
                if any(cell.strip() for cell in extras):
                    fail(f"unheaded data in {path.relative_to(ROOT)} line {line_no}: {extras!r}")
                row = row[:len(header)]
                row_width_changed = True
            if len(row) < len(header):
                row = row + [""] * (len(header) - len(row))
                row_width_changed = True
            new_rows.append([row[index[column]] if column in index else "" for column in canonical])
        if header != canonical or row_width_changed:
            write_rows(path, new_rows)
            changed.append(str(path.relative_to(ROOT)))
    print("normalized:", ", ".join(changed) if changed else "no changes")
    return changed


def load_dict_rows(path, expected_header):
    rows = read_rows(path)
    if not rows:
        fail(f"empty CSV: {path.relative_to(ROOT)}")
    if rows[0] != expected_header:
        fail(
            f"schema mismatch in {path.relative_to(ROOT)}\n"
            f"expected: {expected_header!r}\n"
            f"actual:   {rows[0]!r}"
        )
    result = []
    for line_no, row in enumerate(rows[1:], start=2):
        if not row or not any(cell != "" for cell in row):
            continue
        if len(row) > len(expected_header) and any(cell.strip() for cell in row[len(expected_header):]):
            fail(f"unheaded data in {path.relative_to(ROOT)} line {line_no}")
        padded = row[:len(expected_header)] + [""] * max(0, len(expected_header) - len(row))
        result.append((line_no, dict(zip(expected_header, padded))))
    return result


def split_ids(value):
    return [part.strip() for part in (value or "").split(",") if part.strip()]


def require_unique(rows, columns, label):
    seen = {}
    for line_no, row in rows:
        key = tuple((row.get(column) or "").strip() for column in columns)
        if not all(key):
            continue
        if key in seen:
            fail(f"duplicate {label} {key!r}: lines {seen[key]} and {line_no}")
        seen[key] = line_no


def validate_required(rows, required_columns, path):
    for line_no, row in rows:
        for column in required_columns:
            if not (row.get(column) or "").strip():
                fail(f"blank required {column} in {path.relative_to(ROOT)} line {line_no}")


def validate():
    schemas, required = load_schema()
    loaded = {}
    for scope, owner, file_name, path in specs(schemas):
        if not path.is_file():
            fail(f"missing CSV: {path.relative_to(ROOT)}")
        rows = load_dict_rows(path, schemas[(scope, file_name)])
        validate_required(rows, required[(scope, file_name)], path)
        loaded[(owner, file_name)] = rows

    universal_abilities = {
        (row["Ability_ID"] or "").strip()
        for _, row in loaded[("universal", "Universal_Abilities.csv")]
        if (row["Ability_ID"] or "").strip()
    }
    require_unique(loaded[("universal", "Universal_Abilities.csv")], ["Ability_ID"], "universal Ability_ID")
    require_unique(loaded[("universal", "Universal_Stratagems.csv")], ["Item_ID"], "universal Item_ID")
    for line_no, row in loaded[("universal", "Universal_Stratagems.csv")]:
        item_type = (row.get("Item_Type") or "").strip().upper()
        if item_type not in ALLOWED_UNIVERSAL_TYPES:
            fail(f"invalid universal Item_Type {item_type!r} line {line_no}")

    for army in ARMIES:
        units = loaded[(army, "Units.csv")]
        weapons = loaded[(army, "Weapon_Stats.csv")]
        abilities = loaded[(army, "Abilities.csv")]
        detachments = loaded[(army, "Detachments.csv")]
        options = loaded[(army, "Unit_Weapon_Options.csv")]

        require_unique(units, ["Unit_ID"], f"{army} Unit_ID")
        require_unique(weapons, ["Weapon_ID"], f"{army} Weapon_ID")
        require_unique(abilities, ["Ability_ID"], f"{army} Ability_ID")
        require_unique(detachments, ["Item_ID"], f"{army} Item_ID")
        require_unique(options, ["Unit_ID", "Option_Group_ID", "Option_ID"], f"{army} weapon option")

        unit_ids = {(row["Unit_ID"] or "").strip() for _, row in units}
        weapon_ids = {(row["Weapon_ID"] or "").strip() for _, row in weapons}
        army_ability_ids = {(row["Ability_ID"] or "").strip() for _, row in abilities}
        all_ability_ids = army_ability_ids | universal_abilities

        for line_no, row in units:
            unit_id = (row["Unit_ID"] or "").strip()
            for weapon_id in split_ids(row.get("Weapon_IDs")):
                if weapon_id not in weapon_ids:
                    fail(f"{army} unit {unit_id}: missing Weapon_ID {weapon_id!r} (line {line_no})")
            for ability_id in split_ids(row.get("Ability_IDs")):
                if ability_id not in all_ability_ids:
                    fail(f"{army} unit {unit_id}: missing Ability_ID {ability_id!r} (line {line_no})")
            for ability_id in split_ids(row.get("Core_Ability_IDs")):
                if ability_id not in all_ability_ids:
                    fail(f"{army} unit {unit_id}: missing Core_Ability_ID {ability_id!r} (line {line_no})")

        option_groups = defaultdict(list)
        option_index = defaultdict(lambda: defaultdict(set))
        for line_no, row in options:
            unit_id = (row["Unit_ID"] or "").strip()
            group_id = (row["Option_Group_ID"] or "").strip()
            option_id = (row["Option_ID"] or "").strip()
            if unit_id not in unit_ids:
                fail(f"{army} option {option_id}: missing Unit_ID {unit_id!r} (line {line_no})")
            for weapon_id in split_ids(row.get("Weapon_IDs")) + split_ids(row.get("Preserve_Weapon_IDs")):
                if weapon_id not in weapon_ids:
                    fail(f"{army} option {option_id}: missing Weapon_ID {weapon_id!r} (line {line_no})")
            for ability_id in split_ids(row.get("Ability_IDs")):
                if ability_id not in all_ability_ids:
                    fail(f"{army} option {option_id}: missing Ability_ID {ability_id!r} (line {line_no})")
            option_groups[(unit_id, group_id)].append((line_no, row))
            option_index[unit_id][group_id].add(option_id)

        for (unit_id, group_id), group_rows in option_groups.items():
            defaults = [
                line_no for line_no, row in group_rows
                if (row.get("Default") or "").strip().lower() in TRUE_VALUES
            ]
            if len(defaults) != 1:
                fail(f"{army} {unit_id}/{group_id}: expected exactly one Default, found {len(defaults)}")

        for line_no, row in options:
            unit_id = (row["Unit_ID"] or "").strip()
            option_id = (row["Option_ID"] or "").strip()
            compat = (row.get("Compatible_With") or "").strip()
            if not compat:
                continue
            for raw_rule in compat.split(";"):
                rule = raw_rule.strip()
                if not rule:
                    continue
                sep = "=" if "=" in rule else (":" if ":" in rule else None)
                if not sep:
                    fail(f"{army} option {option_id}: invalid Compatible_With rule {rule!r} (line {line_no})")
                group_id, option_text = rule.split(sep, 1)
                group_id = group_id.strip()
                allowed = [value.strip() for value in option_text.split("|") if value.strip()]
                if group_id not in option_index[unit_id]:
                    fail(f"{army} option {option_id}: unknown compatible group {group_id!r} (line {line_no})")
                unknown_options = [value for value in allowed if value not in option_index[unit_id][group_id]]
                if unknown_options:
                    fail(f"{army} option {option_id}: unknown compatible options {unknown_options!r} (line {line_no})")

        for line_no, row in detachments:
            item_type = (row.get("Item_Type") or "").strip().upper()
            if item_type not in ALLOWED_DETACHMENT_TYPES:
                fail(f"{army} invalid Item_Type {item_type!r} line {line_no}")

    print("validation: OK")
    return True


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def generate_manifests():
    schemas, _ = load_schema()
    schema_hash = sha256_bytes(SCHEMA_PATH.read_bytes())
    changed = []
    groups = [(army, "army") for army in ARMIES] + [("universal", "universal")]
    for owner, scope in groups:
        directory = ROOT / "data" / owner
        file_names = sorted(file_name for schema_scope, file_name in schemas if schema_scope == scope)
        file_records = {}
        dataset_material = []
        for file_name in file_names:
            path = directory / file_name
            if not path.is_file():
                fail(f"cannot manifest missing file: {path.relative_to(ROOT)}")
            data = path.read_bytes()
            digest = sha256_bytes(data)
            file_records[file_name] = {"sha256": digest, "bytes": len(data)}
            dataset_material.append(f"{file_name}:{digest}\n")
        dataset_hash = sha256_bytes("".join(dataset_material).encode("utf-8"))
        payload = {
            "schema_version": 1,
            "schema_sha256": schema_hash,
            "dataset_sha256": dataset_hash,
            "files": file_records,
        }
        content = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        manifest = directory / "manifest.json"
        old = manifest.read_text(encoding="utf-8") if manifest.exists() else None
        if old != content:
            manifest.write_text(content, encoding="utf-8")
            changed.append(str(manifest.relative_to(ROOT)))
    print("manifests:", ", ".join(changed) if changed else "no changes")
    return changed


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else "all"
    if command == "normalize":
        normalize()
    elif command == "validate":
        validate()
    elif command in {"manifest", "manifests"}:
        generate_manifests()
    elif command == "all":
        normalize()
        validate()
        generate_manifests()
    else:
        fail("usage: data_schema.py [normalize|validate|manifest|all]")


if __name__ == "__main__":
    main()
