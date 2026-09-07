#!/usr/bin/env python3
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMIES = ("marines", "orks", "nids")
TRUE_VALUES = {"true", "1", "yes", "y"}


def fail(message):
    raise SystemExit(message)


def read_dicts(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [row for row in csv.DictReader(handle) if any((value or "").strip() for value in row.values())]


def split_ids(value):
    return [part.strip() for part in (value or "").split(",") if part.strip()]


def legacy_expected(rows):
    options = []
    weapons = []
    abilities = []
    points = []
    compatibility = []
    legacy_units = []
    for row in rows:
        unit_id = (row.get("Unit_ID") or "").strip()
        group_id = (row.get("Option_Group_ID") or "").strip()
        option_id = (row.get("Option_ID") or "").strip()
        options.append((
            unit_id, group_id, (row.get("Group_Label") or "").strip(), option_id,
            (row.get("Option_Name") or "").strip(), (row.get("Default") or "").strip(),
            (row.get("Sort_Order") or "").strip(),
        ))
        for index, weapon_id in enumerate(split_ids(row.get("Weapon_IDs")), start=1):
            weapons.append((unit_id, group_id, option_id, weapon_id, "SELECTED", str(index)))
        for index, weapon_id in enumerate(split_ids(row.get("Preserve_Weapon_IDs")), start=1):
            weapons.append((unit_id, group_id, option_id, weapon_id, "PRESERVE", str(index)))
        for index, ability_id in enumerate(split_ids(row.get("Ability_IDs")), start=1):
            abilities.append((unit_id, group_id, option_id, ability_id, str(index)))
        for index in range(1, 3):
            label = (row.get(f"Points_Label_{index}") or "").strip()
            cost = (row.get(f"Points_Cost_{index}") or "").strip()
            if label or cost:
                points.append((unit_id, group_id, option_id, f"point_{index}", label, cost, str(index)))
        for rule_order, raw_rule in enumerate((row.get("Compatible_With") or "").split(";"), start=1):
            rule = raw_rule.strip()
            if not rule:
                continue
            sep = "=" if "=" in rule else (":" if ":" in rule else None)
            if not sep:
                fail(f"invalid legacy compatibility rule {rule!r}")
            required_group, option_text = rule.split(sep, 1)
            for option_order, compatible_option in enumerate(
                [part.strip() for part in option_text.split("|") if part.strip()], start=1
            ):
                compatibility.append((
                    unit_id, group_id, option_id, required_group.strip(), compatible_option,
                    str(rule_order), str(option_order),
                ))
        for index, legacy_unit_id in enumerate(split_ids(row.get("Legacy_Unit_IDs")), start=1):
            legacy_units.append((unit_id, group_id, option_id, legacy_unit_id, str(index)))
    return options, weapons, abilities, points, compatibility, legacy_units


def actual_tuples(rows, columns):
    return [tuple((row.get(column) or "").strip() for column in columns) for row in rows]


def validate_army(army):
    directory = ROOT / "data" / army
    legacy = read_dicts(directory / "Unit_Weapon_Options.csv")
    options = read_dicts(directory / "Unit_Loadout_Options.csv")
    weapons = read_dicts(directory / "Unit_Loadout_Weapons.csv")
    abilities = read_dicts(directory / "Unit_Loadout_Abilities.csv")
    points = read_dicts(directory / "Unit_Loadout_Points.csv")
    compatibility = read_dicts(directory / "Unit_Loadout_Compatibility.csv")
    legacy_units = read_dicts(directory / "Unit_Loadout_Legacy_Units.csv")

    expected = legacy_expected(legacy)
    actual = (
        actual_tuples(options, ["Unit_ID", "Option_Group_ID", "Group_Label", "Option_ID", "Option_Name", "Default", "Sort_Order"]),
        actual_tuples(weapons, ["Unit_ID", "Option_Group_ID", "Option_ID", "Weapon_ID", "Weapon_Role", "Sort_Order"]),
        actual_tuples(abilities, ["Unit_ID", "Option_Group_ID", "Option_ID", "Ability_ID", "Sort_Order"]),
        actual_tuples(points, ["Unit_ID", "Option_Group_ID", "Option_ID", "Point_Option_ID", "Label", "Cost", "Sort_Order"]),
        actual_tuples(compatibility, ["Unit_ID", "Option_Group_ID", "Option_ID", "Required_Group_ID", "Compatible_Option_ID", "Rule_Order", "Option_Order"]),
        actual_tuples(legacy_units, ["Unit_ID", "Option_Group_ID", "Option_ID", "Legacy_Unit_ID", "Sort_Order"]),
    )
    labels = ("options", "weapons", "abilities", "points", "compatibility", "legacy units")
    for label, expected_rows, actual_rows in zip(labels, expected, actual):
        if expected_rows != actual_rows:
            fail(f"{army}: normalized loadout {label} do not exactly match legacy Unit_Weapon_Options.csv")

    unit_ids = {(row.get("Unit_ID") or "").strip() for row in read_dicts(directory / "Units.csv")}
    weapon_ids = {(row.get("Weapon_ID") or "").strip() for row in read_dicts(directory / "Weapon_Stats.csv")}
    ability_ids = {(row.get("Ability_ID") or "").strip() for row in read_dicts(directory / "Abilities.csv")}
    universal_ability_ids = {
        (row.get("Ability_ID") or "").strip()
        for row in read_dicts(ROOT / "data" / "universal" / "Universal_Abilities.csv")
    }
    all_ability_ids = ability_ids | universal_ability_ids

    option_keys = set()
    group_options = defaultdict(set)
    defaults = defaultdict(int)
    for row in options:
        unit_id = (row.get("Unit_ID") or "").strip()
        group_id = (row.get("Option_Group_ID") or "").strip()
        option_id = (row.get("Option_ID") or "").strip()
        key = (unit_id, group_id, option_id)
        if unit_id not in unit_ids:
            fail(f"{army}: loadout option {key!r} references missing Unit_ID")
        if key in option_keys:
            fail(f"{army}: duplicate normalized loadout option {key!r}")
        option_keys.add(key)
        group_options[(unit_id, group_id)].add(option_id)
        if (row.get("Default") or "").strip().lower() in TRUE_VALUES:
            defaults[(unit_id, group_id)] += 1
    for group_key in group_options:
        if defaults[group_key] != 1:
            fail(f"{army}: {group_key!r} must have exactly one default")

    for row in weapons:
        key = ((row.get("Unit_ID") or "").strip(), (row.get("Option_Group_ID") or "").strip(), (row.get("Option_ID") or "").strip())
        weapon_id = (row.get("Weapon_ID") or "").strip()
        role = (row.get("Weapon_Role") or "").strip()
        if key not in option_keys:
            fail(f"{army}: loadout weapon references missing option {key!r}")
        if weapon_id not in weapon_ids:
            fail(f"{army}: loadout option {key!r} references missing Weapon_ID {weapon_id!r}")
        if role not in {"SELECTED", "PRESERVE"}:
            fail(f"{army}: loadout option {key!r} has invalid Weapon_Role {role!r}")

    for row in abilities:
        key = ((row.get("Unit_ID") or "").strip(), (row.get("Option_Group_ID") or "").strip(), (row.get("Option_ID") or "").strip())
        ability_id = (row.get("Ability_ID") or "").strip()
        if key not in option_keys:
            fail(f"{army}: loadout ability references missing option {key!r}")
        if ability_id not in all_ability_ids:
            fail(f"{army}: loadout option {key!r} references missing Ability_ID {ability_id!r}")

    for row in points:
        key = ((row.get("Unit_ID") or "").strip(), (row.get("Option_Group_ID") or "").strip(), (row.get("Option_ID") or "").strip())
        if key not in option_keys:
            fail(f"{army}: loadout points reference missing option {key!r}")

    for row in compatibility:
        unit_id = (row.get("Unit_ID") or "").strip()
        key = (unit_id, (row.get("Option_Group_ID") or "").strip(), (row.get("Option_ID") or "").strip())
        required_group = (row.get("Required_Group_ID") or "").strip()
        compatible_option = (row.get("Compatible_Option_ID") or "").strip()
        if key not in option_keys:
            fail(f"{army}: compatibility references missing option {key!r}")
        if compatible_option not in group_options.get((unit_id, required_group), set()):
            fail(f"{army}: compatibility for {key!r} references unknown {required_group}/{compatible_option}")

    print(
        f"{army}: loadouts OK — {len(options)} options, {len(weapons)} weapons, "
        f"{len(abilities)} abilities, {len(points)} points, {len(compatibility)} compatibility rows, "
        f"{len(legacy_units)} legacy aliases"
    )


def main():
    for army in ARMIES:
        validate_army(army)
    print("loadout validation: OK")


if __name__ == "__main__":
    main()
