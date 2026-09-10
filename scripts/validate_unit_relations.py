#!/usr/bin/env python3
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMIES = ("marines", "orks", "nids")
ABILITY_TYPES = {"ABILITY", "CORE_ABILITY"}

PROFILE_HEADER = ["Unit_ID", "Unit Name", 'M"', "T", "SV", "W", "LD", "OC", "Keywords", "Hyperlink"]
UNIT_ABILITIES_HEADER = ["Unit_ID", "Ability_ID", "Ability_Type"]
UNIT_WEAPONS_HEADER = ["Unit_ID", "Weapon_ID"]
UNIT_POINTS_HEADER = ["Unit_ID", "Point_Option_ID", "Label", "Cost", "Sort_Order"]


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
    unit_abilities = read_dicts(directory / "Unit_Abilities.csv", UNIT_ABILITIES_HEADER)
    unit_weapons = read_dicts(directory / "Unit_Weapons.csv", UNIT_WEAPONS_HEADER)
    unit_points = read_dicts(directory / "Unit_Points.csv", UNIT_POINTS_HEADER)

    require_unique(profiles, ["Unit_ID"], "unit profile", army)
    unit_ids = {(row.get("Unit_ID") or "").strip() for row in profiles}
    weapon_ids = {(row.get("Weapon_ID") or "").strip() for row in weapon_stats}
    ability_ids = {
        (row.get("Ability_ID") or "").strip()
        for row in army_abilities
        if (row.get("Ability_ID") or "").strip()
    } | universal_ability_ids

    require_unique(unit_abilities, ["Unit_ID", "Ability_Type", "Ability_ID"], "unit ability relationship", army)
    require_unique(unit_weapons, ["Unit_ID", "Weapon_ID"], "unit weapon relationship", army)
    require_unique(unit_points, ["Unit_ID", "Point_Option_ID"], "unit point option", army)
    require_unique(unit_points, ["Unit_ID", "Sort_Order"], "unit point sort order", army)

    for line_no, row in enumerate(unit_abilities, start=2):
        unit_id = (row.get("Unit_ID") or "").strip()
        ability_id = (row.get("Ability_ID") or "").strip()
        ability_type = (row.get("Ability_Type") or "").strip()
        if unit_id not in unit_ids:
            fail(f"{army}: Unit_Abilities line {line_no} references missing Unit_Profile {unit_id!r}")
        if ability_id not in ability_ids:
            fail(f"{army}: Unit_Abilities line {line_no} references missing Ability_ID {ability_id!r}")
        if ability_type not in ABILITY_TYPES:
            fail(f"{army}: Unit_Abilities line {line_no} has invalid Ability_Type {ability_type!r}")

    for line_no, row in enumerate(unit_weapons, start=2):
        unit_id = (row.get("Unit_ID") or "").strip()
        weapon_id = (row.get("Weapon_ID") or "").strip()
        if unit_id not in unit_ids:
            fail(f"{army}: Unit_Weapons line {line_no} references missing Unit_Profile {unit_id!r}")
        if weapon_id not in weapon_ids:
            fail(f"{army}: Unit_Weapons line {line_no} references missing Weapon_ID {weapon_id!r}")

    for line_no, row in enumerate(unit_points, start=2):
        unit_id = (row.get("Unit_ID") or "").strip()
        option_id = (row.get("Point_Option_ID") or "").strip()
        label = (row.get("Label") or "").strip()
        cost = (row.get("Cost") or "").strip()
        sort_text = (row.get("Sort_Order") or "").strip()
        if unit_id not in unit_ids:
            fail(f"{army}: Unit_Points line {line_no} references missing Unit_Profile {unit_id!r}")
        if not label and not cost:
            fail(f"{army}: Unit_Points line {line_no} has neither Label nor Cost")
        try:
            sort_order = int(sort_text)
        except ValueError:
            fail(f"{army}: Unit_Points line {line_no} has invalid Sort_Order {sort_text!r}")
        if sort_order < 1 or sort_order > 8:
            fail(f"{army}: Unit_Points line {line_no} Sort_Order must be 1-8, got {sort_order}")
        if option_id != f"point_{sort_order}":
            fail(
                f"{army}: Unit_Points line {line_no} Point_Option_ID {option_id!r} "
                f"does not match Sort_Order {sort_order}"
            )

    print(
        f"{army}: unit relations OK — "
        f"{len(unit_abilities)} abilities, {len(unit_weapons)} weapons, {len(unit_points)} point options"
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
