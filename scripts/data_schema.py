#!/usr/bin/env python3
import csv
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "data" / "CSV_SCHEMA.csv"
ARMIES = ("marines", "orks", "nids")
ALLOWED_UNIVERSAL_TYPES = {"CORE_STRATAGEM", "STRATAGEM"}
ALLOWED_OWNERSHIP = {"AUTHORITATIVE"}
RETIRED_COLUMNS_BY_FILE = {
    ("army", "Abilities.csv"): {"Tag Categories"},
    ("army", "Detachment_Definitions.csv"): {"Tag Categories"},
    ("army", "Enhancements.csv"): {"Tag Categories"},
    ("army", "Stratagems.csv"): {"Tag Categories"},
    ("army", "Army_Rules.csv"): {"Tag Categories"},
    ("army", "Weapon_Abilities.csv"): {"Separator_Before"},
}


def fail(message):
    raise SystemExit(message)


def load_schema():
    if not SCHEMA_PATH.is_file():
        fail(f"missing schema: {SCHEMA_PATH}")
    grouped = defaultdict(list)
    required = defaultdict(set)
    ownership_by_file = defaultdict(set)
    with SCHEMA_PATH.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        expected = ["Scope", "File", "Column_Order", "Column_Name", "Required", "Ownership", "Notes"]
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
            ownership = (row.get("Ownership") or "").strip().upper()
            if ownership not in ALLOWED_OWNERSHIP:
                fail(f"invalid Ownership {ownership!r} in schema row: {row!r}")
            ownership_by_file[(scope, file_name)].add(ownership)
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
            fail(f"missing required CSV: {path.relative_to(ROOT)}")
        rows = read_rows(path)
        if not rows:
            fail(f"empty CSV: {path.relative_to(ROOT)}")
        header = rows[0]
        if len(header) != len(set(header)):
            fail(f"duplicate header in {path.relative_to(ROOT)}: {header!r}")
        retired_columns = RETIRED_COLUMNS_BY_FILE.get((scope, file_name), set())
        unknown = [column for column in header if column not in canonical and column not in retired_columns]
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


def validate_effect_groups(rows, key_column, label, detachment_scoped=False):
    """Validate one parent-owned ordered Effect_IDs list; return all child IDs."""
    by_id = {(row.get(key_column) or "").strip(): row for _, row in rows}
    children = set()
    for line_no, row in rows:
        parent_id = (row.get(key_column) or "").strip()
        ids = split_ids(row.get("Effect_IDs"))
        if len(ids) != len(set(ids)):
            fail(f"{label} line {line_no}: duplicate Effect_IDs")
        for child_id in ids:
            if child_id == parent_id:
                fail(f"{label} line {line_no}: Effect_IDs cannot include its own ID")
            child = by_id.get(child_id)
            if child is None:
                fail(f"{label} line {line_no}: unknown Effect_ID {child_id!r}")
            if child_id in children:
                fail(f"{label} line {line_no}: child Effect_ID {child_id!r} has multiple parents")
            if split_ids(child.get("Effect_IDs")):
                fail(f"{label} line {line_no}: nested Effect_IDs not supported: {child_id!r}")
            if detachment_scoped and (row.get("Detachment_ID") or "").strip() != (child.get("Detachment_ID") or "").strip():
                fail(f"{label} line {line_no}: child Effect_ID {child_id!r} belongs to another Detachment_ID")
            children.add(child_id)
    return children


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
        unit_profiles = loaded[(army, "Unit_Profiles.csv")]
        weapons = loaded[(army, "Weapon_Stats.csv")]
        weapon_abilities = loaded[(army, "Weapon_Abilities.csv")]
        abilities = loaded[(army, "Abilities.csv")]
        detachment_definitions = loaded[(army, "Detachment_Definitions.csv")]
        enhancements = loaded[(army, "Enhancements.csv")]
        stratagems = loaded[(army, "Stratagems.csv")]
        army_rules = loaded[(army, "Army_Rules.csv")]

        require_unique(unit_profiles, ["Unit_ID"], f"{army} authoritative Unit_ID")
        require_unique(weapons, ["Weapon_ID"], f"{army} Weapon_ID")
        require_unique(weapon_abilities, ["Weapon_Ability_ID"], f"{army} Weapon_Ability_ID")
        require_unique(abilities, ["Ability_ID"], f"{army} Ability_ID")
        require_unique(detachment_definitions, ["Rule_ID"], f"{army} detachment Rule_ID")
        require_unique(enhancements, ["Enhancement_ID"], f"{army} Enhancement_ID")
        validate_effect_groups(abilities, "Ability_ID", f"{army} Abilities")
        detachment_effect_children = validate_effect_groups(
            detachment_definitions, "Rule_ID", f"{army} Detachment_Definitions", detachment_scoped=True
        )
        validate_effect_groups(enhancements, "Enhancement_ID", f"{army} Enhancements", detachment_scoped=True)
        # Child detachment-rule rows share their parent's Detachment_ID by design.
        # Every parent owns one unique detachment definition.
        detachment_parents = [
            (line_no, row) for line_no, row in detachment_definitions
            if (row.get("Rule_ID") or "").strip() not in detachment_effect_children
        ]
        require_unique(detachment_parents, ["Detachment_ID"], f"{army} Detachment_ID")
        require_unique(stratagems, ["Stratagem_ID"], f"{army} Stratagem_ID")
        require_unique(army_rules, ["Army_Rule_ID"], f"{army} Army_Rule_ID")

        unit_ids = {(row["Unit_ID"] or "").strip() for _, row in unit_profiles}
        weapon_ids = {(row["Weapon_ID"] or "").strip() for _, row in weapons}
        army_ability_ids = {(row["Ability_ID"] or "").strip() for _, row in abilities}
        all_ability_ids = army_ability_ids | universal_abilities
        detachment_ids = {(row["Detachment_ID"] or "").strip() for _, row in detachment_definitions}

        for line_no, row in unit_profiles:
            unit_id = (row.get("Unit_ID") or "").strip()
            core = split_ids(row.get("Abilities"))
            other = split_ids(row.get("Other_Abilities"))
            for column, ids in (("Abilities", core), ("Other_Abilities", other)):
                if len(ids) != len(set(ids)):
                    fail(f"{army} Unit_Profiles line {line_no}: duplicate Ability_ID in {column}")
                for ability_id in ids:
                    if ability_id not in all_ability_ids:
                        fail(f"{army} Unit_Profiles line {line_no}: unknown Ability_ID {ability_id!r} in {column}")
            if set(core) & set(other):
                fail(f"{army} Unit_Profiles line {line_no}: duplicate Ability_ID across Abilities and Other_Abilities")
            for slot in range(1, 9):
                column = f"Point_{slot}"
                value = (row.get(column) or "").strip()
                if not value:
                    continue
                if "," not in value:
                    fail(f"{army} Unit_Profiles line {line_no}: {column} requires label, cost")
                label, cost = (part.strip() for part in value.rsplit(",", 1))
                if not label and not cost:
                    fail(f"{army} Unit_Profiles line {line_no}: blank {column}")
                if cost and (not cost.isascii() or not cost.isdecimal()):
                    fail(f"{army} Unit_Profiles line {line_no}: invalid {column} cost {cost!r}")

        for line_no, row in weapon_abilities:
            weapon_id = (row["Weapon_ID"] or "").strip()
            if weapon_id not in weapon_ids:
                fail(f"{army} Weapon_Abilities line {line_no}: missing Weapon_ID {weapon_id!r}")

        from validate_loadouts import validate_army as validate_embedded_loadouts
        validate_embedded_loadouts(army)

        for line_no, row in enhancements:
            enhancement_id = (row["Enhancement_ID"] or "").strip()
            detachment_id = (row["Detachment_ID"] or "").strip()
            if detachment_id not in detachment_ids:
                fail(
                    f"{army} enhancement {enhancement_id}: missing Detachment_ID "
                    f"{detachment_id!r} (line {line_no})"
                )

        for line_no, row in stratagems:
            stratagem_id = (row["Stratagem_ID"] or "").strip()
            detachment_id = (row["Detachment_ID"] or "").strip()
            if detachment_id not in detachment_ids:
                fail(
                    f"{army} stratagem {stratagem_id}: missing Detachment_ID "
                    f"{detachment_id!r} (line {line_no})"
                )

    validate_tag_contract(loaded)
    print("validation: OK")
    return True


TAG_BRACKET = re.compile(r"\[([^\[\]]+)\]")
TAGGED_ARMY_FILES = (
    "Abilities.csv",
    "Enhancements.csv",
    "Stratagems.csv",
    "Detachment_Definitions.csv",
    "Army_Rules.csv",
)
CONTROL_TAGS = {"UNIT", "ROSTER", "ROSTER_ALL", "ACTIVE", "PERSISTENT", "SHOOT", "MELEE", "STATS", "WEAPONS", "GRANT_IMPERIUM_SWORD"}
EFFECT_FIELDS = ("Effect_Type", "Target", "Stat", "Operation", "Value")


def normalize_tag_key(value):
    return (
        str(value or "")
        .strip()
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2019", "'")
        .upper()
    )


def normalize_category_key(value):
    return (
        str(value or "")
        .strip()
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .lower()
    )


def validate_tag_contract(loaded):
    library = {}
    for line_no, row in loaded[("universal", "Tag_Definitions.csv")]:
        display = (row.get("Display_Tag") or "").strip()
        category = (row.get("Category") or "").strip()
        if not display or not category:
            fail(f"Tag_Definitions line {line_no}: Display_Tag and Category are required")
        effect_type = (row.get("Effect_Type") or "").strip()
        target = (row.get("Target") or "").strip()
        stat = (row.get("Stat") or "").strip()
        operation = (row.get("Operation") or "").strip()
        value = (row.get("Value") or "").strip()
        core_effect = [effect_type, stat, operation, value]
        if any(core_effect) and not all(core_effect):
            fail(
                f"Tag_Definitions line {line_no} {display!r}: "
                "Effect_Type/Stat/Operation/Value must all be filled when an executable effect is defined; Target may be blank when scope is supplied by the owning Ability controls."
            )
        if target and not any(core_effect):
            fail(
                f"Tag_Definitions line {line_no} {display!r}: "
                "Target cannot be populated without an executable effect."
            )
        key = normalize_tag_key(display)
        if key in library:
            fail(f"duplicate Tag_Definitions Display_Tag {display!r} (line {line_no})")
        library[key] = row

    for army in ARMIES:
        for file_name in TAGGED_ARMY_FILES:
            for line_no, row in loaded[(army, file_name)]:
                tags = TAG_BRACKET.findall(row.get("Tags") or "")
                visible_tags = [
                    tag for tag in tags
                    if normalize_tag_key(tag) not in CONTROL_TAGS
                ]
                for tag in visible_tags:
                    key = normalize_tag_key(tag)
                    if key not in library:
                        fail(
                            f"{army} {file_name} line {line_no}: "
                            f"[{tag}] is not in Tag_Definitions.csv"
                        )


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
            "schema_version": 2,
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
