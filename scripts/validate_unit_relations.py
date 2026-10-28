#!/usr/bin/env python3
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMIES = ("marines", "orks", "nids")

PROFILE_HEADER = ["Unit_ID", "Unit Name", 'M"', "T", "SV", "W", "LD", "OC", "Keywords", "Hyperlink", "Abilities", "Other_Abilities", *[f"Point_{i}" for i in range(1, 9)]]
UNIT_WEAPONS_HEADER = ["Unit_ID", "Layout_Row_ID", "Weapon_ID", "Row_Type", "Row_Label", "Sort_Order", "Quantity"]


def fail(message):
    raise SystemExit(message)


def read_dicts(path, expected_header=None):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if expected_header is not None and reader.fieldnames != expected_header:
            fail(
                f"{path.relative_to(ROOT)} header mismatch\n"
                f"expected: {expected_header!r}\n"
                f"actual:   {reader.fieldnames!r}"
            )
        rows = list(reader)
    return [row for row in rows if any((value or "").strip() for value in row.values())]


def require_unique(rows, columns, label, army):
    seen = set()
    for line_no, row in enumerate(rows, start=2):
        key = tuple((row.get(column) or "").strip() for column in columns)
        if not all(key):
            fail(f"{army}: blank key component for {label} at line {line_no}: {key!r}")
        if key in seen:
            fail(f"{army}: duplicate {label} {key!r} at line {line_no}")
        seen.add(key)


def validate_army(army, universal_ability_ids):
    directory = ROOT / "data" / army
    profiles = read_dicts(directory / "Unit_Profiles.csv", PROFILE_HEADER)
    weapon_stats = read_dicts(directory / "Weapon_Stats.csv")
    army_abilities = read_dicts(directory / "Abilities.csv")
    unit_weapons = read_dicts(directory / "Unit_Weapons.csv", UNIT_WEAPONS_HEADER)

    require_unique(profiles, ["Unit_ID"], "unit profile", army)
    unit_ids = {(row.get("Unit_ID") or "").strip() for row in profiles}
    weapon_ids = {(row.get("Weapon_ID") or "").strip() for row in weapon_stats}
    ability_ids = {
        (row.get("Ability_ID") or "").strip()
        for row in army_abilities
        if (row.get("Ability_ID") or "").strip()
    } | universal_ability_ids

    seen_unit_weapon_rows = set()
    for line_no, row in enumerate(unit_weapons, start=2):
        key = tuple((row.get(column) or "").strip() for column in UNIT_WEAPONS_HEADER)
        if key in seen_unit_weapon_rows:
            fail(f"{army}: duplicate Unit_Weapons row at line {line_no}: {key!r}")
        seen_unit_weapon_rows.add(key)

    ability_count = 0
    point_count = 0
    for line_no, row in enumerate(profiles, start=2):
        core = [part.strip() for part in (row.get("Abilities") or "").split(",") if part.strip()]
        other = [part.strip() for part in (row.get("Other_Abilities") or "").split(",") if part.strip()]
        for column, ids in (("Abilities", core), ("Other_Abilities", other)):
            if len(set(ids)) != len(ids):
                fail(f"{army}: Unit_Profiles line {line_no} duplicate Ability_ID in {column}")
            for ability_id in ids:
                if ability_id not in ability_ids:
                    fail(f"{army}: Unit_Profiles line {line_no} unknown Ability_ID {ability_id!r} in {column}")
            ability_count += len(ids)
        if set(core) & set(other):
            fail(f"{army}: Unit_Profiles line {line_no} duplicated core/non-core Ability_ID")
        if not (row.get("Point_1") or "").strip():
            fail(f"{army}: Unit_Profiles line {line_no} missing Point_1")
        for slot in range(1, 9):
            col = f"Point_{slot}"
            value = (row.get(col) or "").strip()
            if not value:
                continue
            if "," not in value:
                fail(f"{army}: Unit_Profiles line {line_no} {col} requires label, cost")
            label, cost = (part.strip() for part in value.rsplit(",", 1))
            if not label and not cost:
                fail(f"{army}: Unit_Profiles line {line_no} blank {col}")
            if cost and (not cost.isascii() or not cost.isdecimal()):
                fail(f"{army}: Unit_Profiles line {line_no} invalid {col} cost {cost!r}")
            point_count += 1

    for line_no, row in enumerate(unit_weapons, start=2):
        unit_id = (row.get("Unit_ID") or "").strip()
        weapon_id = (row.get("Weapon_ID") or "").strip()
        row_type = (row.get("Row_Type") or "WEAPON").strip().upper()
        row_label = (row.get("Row_Label") or "").strip()
        quantity = (row.get("Quantity") or "").strip()
        sort_order = (row.get("Sort_Order") or "").strip()
        if unit_id not in unit_ids:
            fail(f"{army}: Unit_Weapons line {line_no} references missing Unit_Profile {unit_id!r}")
        if row_type not in {"WEAPON", "LABEL", "BLANK"}:
            fail(f"{army}: Unit_Weapons line {line_no} has invalid Row_Type {row_type!r}")
        if row_type == "WEAPON":
            if not weapon_id or weapon_id not in weapon_ids:
                fail(f"{army}: Unit_Weapons line {line_no} references missing Weapon_ID {weapon_id!r}")
            if row_label:
                fail(f"{army}: Unit_Weapons line {line_no} WEAPON row must have blank Row_Label")
        elif row_type == "LABEL":
            if weapon_id or not row_label:
                fail(f"{army}: Unit_Weapons line {line_no} LABEL row requires blank Weapon_ID and nonblank Row_Label")
            if quantity:
                fail(f"{army}: Unit_Weapons line {line_no} LABEL row requires blank Quantity")
        else:
            if weapon_id or row_label or quantity:
                fail(f"{army}: Unit_Weapons line {line_no} BLANK row requires blank Weapon_ID, Row_Label, and Quantity")
        if sort_order:
            try:
                int(sort_order)
            except ValueError:
                fail(f"{army}: Unit_Weapons line {line_no} has invalid Sort_Order {sort_order!r}")
        if quantity:
            try:
                parsed_quantity = int(quantity)
            except ValueError:
                fail(f"{army}: Unit_Weapons line {line_no} has invalid Quantity {quantity!r}")
            if parsed_quantity < 0:
                fail(f"{army}: Unit_Weapons line {line_no} Quantity must be >= 0")

    print(
        f"{army}: unit relations OK — "
        f"{ability_count} abilities, {len(unit_weapons)} weapons, {point_count} point options"
    )


def main():
    universal_rows = read_dicts(ROOT / "data" / "universal" / "Universal_Abilities.csv")
    universal_ability_ids = {
        (row.get("Ability_ID") or "").strip()
        for row in universal_rows
        if (row.get("Ability_ID") or "").strip()
    }
    for army in ARMIES:
        validate_army(army, universal_ability_ids)
    print("authoritative unit profile and relationship validation: OK")


if __name__ == "__main__":
    main()
