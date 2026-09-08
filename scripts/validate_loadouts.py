#!/usr/bin/env python3
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMIES = ("marines", "orks", "nids")
TRUE_VALUES = {"true", "1", "yes", "y"}

CANON = {
    "Loadout_Options.csv": [
        "Loadout_Option_ID", "Unit_ID", "Option_Group_ID", "Group_Label", "Option_ID",
        "Option_Name", "Default", "Sort_Order",
    ],
    "Loadout_Weapons.csv": ["Loadout_Option_ID", "Weapon_ID", "Weapon_Role", "Sort_Order"],
    "Loadout_Abilities.csv": ["Loadout_Option_ID", "Ability_ID", "Sort_Order"],
    "Loadout_Points.csv": ["Loadout_Option_ID", "Point_Option_ID", "Label", "Cost", "Sort_Order"],
    "Loadout_Compatibility.csv": [
        "Loadout_Option_ID", "Required_Group_ID", "Compatible_Option_ID", "Rule_Order", "Option_Order",
    ],
}
COMPAT = {
    "Unit_Loadout_Options.csv": [
        "Unit_ID", "Option_Group_ID", "Group_Label", "Option_ID", "Option_Name", "Default", "Sort_Order",
    ],
    "Unit_Loadout_Weapons.csv": [
        "Unit_ID", "Option_Group_ID", "Option_ID", "Weapon_ID", "Weapon_Role", "Sort_Order",
    ],
    "Unit_Loadout_Abilities.csv": ["Unit_ID", "Option_Group_ID", "Option_ID", "Ability_ID", "Sort_Order"],
    "Unit_Loadout_Points.csv": [
        "Unit_ID", "Option_Group_ID", "Option_ID", "Point_Option_ID", "Label", "Cost", "Sort_Order",
    ],
    "Unit_Loadout_Compatibility.csv": [
        "Unit_ID", "Option_Group_ID", "Option_ID", "Required_Group_ID",
        "Compatible_Option_ID", "Rule_Order", "Option_Order",
    ],
}


def fail(message):
    raise SystemExit(message)


def read_dicts(path, expected_header=None):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if expected_header is not None and reader.fieldnames != expected_header:
            fail(
                f"{path.relative_to(ROOT)} header mismatch\n"
                f"expected: {expected_header!r}\nactual:   {reader.fieldnames!r}"
            )
        return [row for row in reader if any((value or "").strip() for value in row.values())]


def clean(value):
    return (value or "").strip()


def split_ids(value):
    return [part.strip() for part in (value or "").split(",") if part.strip()]


def actual_tuples(rows, columns):
    return [tuple(clean(row.get(column)) for column in columns) for row in rows]


def legacy_expected(rows):
    options = []
    weapons = []
    abilities = []
    points = []
    compatibility = []
    for row in rows:
        unit_id = clean(row.get("Unit_ID"))
        group_id = clean(row.get("Option_Group_ID"))
        option_id = clean(row.get("Option_ID"))
        options.append((
            unit_id, group_id, clean(row.get("Group_Label")), option_id,
            clean(row.get("Option_Name")), clean(row.get("Default")), clean(row.get("Sort_Order")),
        ))
        for index, weapon_id in enumerate(split_ids(row.get("Weapon_IDs")), start=1):
            weapons.append((unit_id, group_id, option_id, weapon_id, "SELECTED", str(index)))
        for index, weapon_id in enumerate(split_ids(row.get("Preserve_Weapon_IDs")), start=1):
            weapons.append((unit_id, group_id, option_id, weapon_id, "PRESERVE", str(index)))
        for index, ability_id in enumerate(split_ids(row.get("Ability_IDs")), start=1):
            abilities.append((unit_id, group_id, option_id, ability_id, str(index)))
        for index in range(1, 3):
            label = clean(row.get(f"Points_Label_{index}"))
            cost = clean(row.get(f"Points_Cost_{index}"))
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
    return options, weapons, abilities, points, compatibility


def expected_compat_from_canonical(canonical):
    options, weapons, abilities, points, compatibility = canonical
    by_id = {clean(row["Loadout_Option_ID"]): row for row in options}

    def parent(row):
        p = by_id[clean(row["Loadout_Option_ID"])]
        return p["Unit_ID"], p["Option_Group_ID"], p["Option_ID"]

    return (
        [
            (
                row["Unit_ID"], row["Option_Group_ID"], row["Group_Label"], row["Option_ID"],
                row["Option_Name"], row["Default"], row["Sort_Order"],
            )
            for row in options
        ],
        [
            (*parent(row), row["Weapon_ID"], row["Weapon_Role"], row["Sort_Order"])
            for row in weapons
        ],
        [
            (*parent(row), row["Ability_ID"], row["Sort_Order"])
            for row in abilities
        ],
        [
            (*parent(row), row["Point_Option_ID"], row["Label"], row["Cost"], row["Sort_Order"])
            for row in points
        ],
        [
            (*parent(row), row["Required_Group_ID"], row["Compatible_Option_ID"], row["Rule_Order"], row["Option_Order"])
            for row in compatibility
        ],
    )


def validate_army(army):
    directory = ROOT / "data" / army
    canonical = tuple(read_dicts(directory / filename, header) for filename, header in CANON.items())
    compat_rows = tuple(read_dicts(directory / filename, header) for filename, header in COMPAT.items())
    options, weapons, abilities, points, compatibility = canonical
    compat_options, compat_weapons, compat_abilities, compat_points, compat_compatibility = compat_rows

    # Canonical IDs and semantic identity.
    by_id = {}
    semantic = set()
    groups = defaultdict(set)
    defaults = defaultdict(int)
    for row in options:
        lid = clean(row["Loadout_Option_ID"])
        unit_id = clean(row["Unit_ID"])
        group_id = clean(row["Option_Group_ID"])
        option_id = clean(row["Option_ID"])
        key = (unit_id, group_id, option_id)
        if not lid:
            fail(f"{army}: blank Loadout_Option_ID")
        if lid in by_id:
            fail(f"{army}: duplicate Loadout_Option_ID {lid!r}")
        if key in semantic:
            fail(f"{army}: duplicate semantic loadout option {key!r}")
        by_id[lid] = row
        semantic.add(key)
        groups[(unit_id, group_id)].add(option_id)
        if clean(row["Default"]).lower() in TRUE_VALUES:
            defaults[(unit_id, group_id)] += 1
    for group_key in groups:
        if defaults[group_key] != 1:
            fail(f"{army}: {group_key!r} must have exactly one default option")

    for filename, rows in zip(list(CANON)[1:], canonical[1:]):
        seen = set()
        for row in rows:
            lid = clean(row["Loadout_Option_ID"])
            if lid not in by_id:
                fail(f"{army}: {filename} references missing Loadout_Option_ID {lid!r}")
            if filename in {"Loadout_Weapons.csv", "Loadout_Abilities.csv", "Loadout_Points.csv"}:
                natural = tuple(clean(row[c]) for c in CANON[filename])
                if natural in seen:
                    fail(f"{army}: duplicate row in {filename}: {natural!r}")
                seen.add(natural)

    # Canonical -> current Unit_Loadout_* compatibility must be exact.
    expected_compat = expected_compat_from_canonical(canonical)
    actual_compat = tuple(
        actual_tuples(rows, header)
        for rows, header in zip(compat_rows, COMPAT.values())
    )
    labels = ("options", "weapons", "abilities", "points", "compatibility")
    for label, expected_rows, actual_rows in zip(labels, expected_compat, actual_compat):
        if expected_rows != actual_rows:
            fail(f"{army}: generated Unit_Loadout_* {label} do not exactly match canonical Loadout_* data")

    # Current Unit_Weapon_Options compatibility must still expand to the current Unit_Loadout_* tables.
    legacy = read_dicts(directory / "Unit_Weapon_Options.csv")
    legacy_rows = legacy_expected(legacy)
    for label, expected_rows, actual_rows in zip(labels, legacy_rows, actual_compat):
        if expected_rows != actual_rows:
            fail(f"{army}: Unit_Weapon_Options {label} do not exactly match generated Unit_Loadout_* data")

    unit_ids = {clean(row.get("Unit_ID")) for row in read_dicts(directory / "Unit_Profiles.csv")}
    weapon_ids = {clean(row.get("Weapon_ID")) for row in read_dicts(directory / "Weapon_Stats.csv")}
    ability_ids = {clean(row.get("Ability_ID")) for row in read_dicts(directory / "Abilities.csv")}
    universal_ability_ids = {
        clean(row.get("Ability_ID"))
        for row in read_dicts(ROOT / "data" / "universal" / "Universal_Abilities.csv")
    }
    all_ability_ids = ability_ids | universal_ability_ids

    for lid, row in by_id.items():
        if clean(row["Unit_ID"]) not in unit_ids:
            fail(f"{army}: loadout {lid!r} references missing Unit_ID {row['Unit_ID']!r}")

    for row in weapons:
        lid = clean(row["Loadout_Option_ID"])
        weapon_id = clean(row["Weapon_ID"])
        role = clean(row["Weapon_Role"])
        if weapon_id not in weapon_ids:
            fail(f"{army}: loadout {lid!r} references missing Weapon_ID {weapon_id!r}")
        if role not in {"SELECTED", "PRESERVE"}:
            fail(f"{army}: loadout {lid!r} has invalid Weapon_Role {role!r}")

    for row in abilities:
        lid = clean(row["Loadout_Option_ID"])
        ability_id = clean(row["Ability_ID"])
        if ability_id not in all_ability_ids:
            fail(f"{army}: loadout {lid!r} references missing Ability_ID {ability_id!r}")

    for row in compatibility:
        lid = clean(row["Loadout_Option_ID"])
        parent = by_id[lid]
        required_group = clean(row["Required_Group_ID"])
        compatible_option = clean(row["Compatible_Option_ID"])
        if compatible_option not in groups.get((clean(parent["Unit_ID"]), required_group), set()):
            fail(
                f"{army}: compatibility for {lid!r} references unknown "
                f"{required_group}/{compatible_option}"
            )

    print(
        f"{army}: loadouts OK — {len(options)} Loadout_Option_IDs, {len(weapons)} weapons, "
        f"{len(abilities)} abilities, {len(points)} points, {len(compatibility)} compatibility rows"
    )


def main():
    for army in ARMIES:
        validate_army(army)
    print("canonical Loadout_Option_ID validation: OK")


if __name__ == "__main__":
    main()
