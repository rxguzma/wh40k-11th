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


def validate_army(army):
    directory = ROOT / "data" / army
    canonical = tuple(read_dicts(directory / filename, header) for filename, header in CANON.items())
    options, weapons, abilities, points, compatibility = canonical

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
