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


def split_ids(value):
    return [part.strip() for part in (value or "").split(",") if part.strip()]


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


def expected_from_units(units):
    abilities = []
    weapons = []
    points = []
    for unit in units:
        unit_id = (unit.get("Unit_ID") or "").strip()
        for ability_type, source_column in (
            ("ABILITY", "Ability_IDs"),
            ("CORE_ABILITY", "Core_Ability_IDs"),
        ):
            for ability_id in split_ids(unit.get(source_column)):
                abilities.append([unit_id, ability_id, ability_type])
        for weapon_id in split_ids(unit.get("Weapon_IDs")):
            weapons.append([unit_id, weapon_id])
        for index in range(1, 9):
            label = (unit.get(f"Points_Label_{index}") or "").strip()
            cost = (unit.get(f"Points_Cost_{index}") or "").strip()
            if not label and not cost:
                continue
            points.append([unit_id, f"point_{index}", label, cost, str(index)])
    return abilities, weapons, points


def actual_rows(rows, header):
    return [[(row.get(column) or "").strip() for column in header] for row in rows]


def normalize_global_unit_order(rows, unit_rank):
    # Relationship order within a unit is semantic; where that unit's block sits in
    # the normalized file is not. Stable-sort only by canonical Units.csv position.
    return sorted(rows, key=lambda row: unit_rank.get(row[0], len(unit_rank)))


def validate_army(army, universal_ability_ids):
    directory = ROOT / "data" / army
    profiles = read_dicts(directory / "Unit_Profiles.csv", PROFILE_HEADER)
    units = read_dicts(directory / "Units.csv")
    weapon_stats = read_dicts(directory / "Weapon_Stats.csv")
    army_abilities = read_dicts(directory / "Abilities.csv")
    unit_abilities = read_dicts(directory / "Unit_Abilities.csv", UNIT_ABILITIES_HEADER)
    unit_weapons = read_dicts(directory / "Unit_Weapons.csv", UNIT_WEAPONS_HEADER)
    unit_points = read_dicts(directory / "Unit_Points.csv", UNIT_POINTS_HEADER)

    require_unique(profiles, ["Unit_ID"], "unit profile", army)
    unit_ids = {(row.get("Unit_ID") or "").strip() for row in profiles}
    unit_rank = {
        (row.get("Unit_ID") or "").strip(): index
        for index, row in enumerate(profiles)
    }
    if len(units) != len(profiles):
        fail(f"{army}: Units.csv row count does not match Unit_Profiles.csv")
    for index, (profile, unit) in enumerate(zip(profiles, units), start=2):
        for column in PROFILE_HEADER:
            if (unit.get(column) or "") != (profile.get(column) or ""):
                fail(f"{army}: Units.csv line {index} profile column {column!r} differs from Unit_Profiles.csv")
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

    expected_abilities, expected_weapons, expected_points = expected_from_units(units)
    actual_abilities = normalize_global_unit_order(actual_rows(unit_abilities, UNIT_ABILITIES_HEADER), unit_rank)
    actual_weapons = normalize_global_unit_order(actual_rows(unit_weapons, UNIT_WEAPONS_HEADER), unit_rank)
    actual_points = normalize_global_unit_order(actual_rows(unit_points, UNIT_POINTS_HEADER), unit_rank)

    if actual_abilities != expected_abilities:
        fail(f"{army}: Unit_Abilities.csv is not an exact per-unit expansion of Units.csv Ability_IDs/Core_Ability_IDs")
    if actual_weapons != expected_weapons:
        fail(f"{army}: Unit_Weapons.csv is not an exact per-unit expansion of Units.csv Weapon_IDs")
    if actual_points != expected_points:
        fail(f"{army}: Unit_Points.csv is not an exact per-unit expansion of Units.csv point slots")

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
