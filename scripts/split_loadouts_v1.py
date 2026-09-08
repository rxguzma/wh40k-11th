#!/usr/bin/env python3
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMIES = ("marines", "orks", "nids")
TRUE_VALUES = {"true", "1", "yes", "y"}

LEGACY_HEADER = [
    "Unit_ID", "Option_Group_ID", "Group_Label", "Option_ID", "Option_Name",
    "Weapon_IDs", "Ability_IDs", "Points_Label_1", "Points_Cost_1",
    "Points_Label_2", "Points_Cost_2", "Default", "Sort_Order",
    "Legacy_Unit_IDs", "Preserve_Weapon_IDs", "Compatible_With",
]
CANON_OPTIONS_HEADER = [
    "Loadout_Option_ID", "Unit_ID", "Option_Group_ID", "Group_Label", "Option_ID",
    "Option_Name", "Default", "Sort_Order",
]
CANON_WEAPONS_HEADER = ["Loadout_Option_ID", "Weapon_ID", "Weapon_Role", "Sort_Order"]
CANON_ABILITIES_HEADER = ["Loadout_Option_ID", "Ability_ID", "Sort_Order"]
CANON_POINTS_HEADER = ["Loadout_Option_ID", "Point_Option_ID", "Label", "Cost", "Sort_Order"]
CANON_COMPAT_HEADER = [
    "Loadout_Option_ID", "Required_Group_ID", "Compatible_Option_ID", "Rule_Order", "Option_Order",
]

COMPAT_OPTIONS_HEADER = [
    "Unit_ID", "Option_Group_ID", "Group_Label", "Option_ID", "Option_Name", "Default", "Sort_Order",
]
COMPAT_WEAPONS_HEADER = [
    "Unit_ID", "Option_Group_ID", "Option_ID", "Weapon_ID", "Weapon_Role", "Sort_Order",
]
COMPAT_ABILITIES_HEADER = ["Unit_ID", "Option_Group_ID", "Option_ID", "Ability_ID", "Sort_Order"]
COMPAT_POINTS_HEADER = [
    "Unit_ID", "Option_Group_ID", "Option_ID", "Point_Option_ID", "Label", "Cost", "Sort_Order",
]
COMPAT_COMPAT_HEADER = [
    "Unit_ID", "Option_Group_ID", "Option_ID", "Required_Group_ID",
    "Compatible_Option_ID", "Rule_Order", "Option_Order",
]
COMPAT_LEGACY_UNITS_HEADER = [
    "Unit_ID", "Option_Group_ID", "Option_ID", "Legacy_Unit_ID", "Sort_Order",
]


def fail(message):
    raise SystemExit(message)


def read_dicts(path, expected_header):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != expected_header:
            fail(
                f"{path.relative_to(ROOT)} header mismatch\n"
                f"expected: {expected_header!r}\n"
                f"actual:   {reader.fieldnames!r}"
            )
        rows = list(reader)
    return [row for row in rows if any((value or "").strip() for value in row.values())]


def write_csv(path, header, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def clean(value):
    return (value or "").strip()


def order_value(value):
    text = clean(value)
    try:
        return int(text)
    except ValueError:
        return 0


def load_canonical(directory):
    options = read_dicts(directory / "Loadout_Options.csv", CANON_OPTIONS_HEADER)
    weapons = read_dicts(directory / "Loadout_Weapons.csv", CANON_WEAPONS_HEADER)
    abilities = read_dicts(directory / "Loadout_Abilities.csv", CANON_ABILITIES_HEADER)
    points = read_dicts(directory / "Loadout_Points.csv", CANON_POINTS_HEADER)
    compatibility = read_dicts(directory / "Loadout_Compatibility.csv", CANON_COMPAT_HEADER)
    return options, weapons, abilities, points, compatibility


def validate_canonical(army, tables):
    options, weapons, abilities, points, compatibility = tables
    by_id = {}
    group_defaults = defaultdict(int)
    group_options = defaultdict(set)

    for row in options:
        lid = clean(row.get("Loadout_Option_ID"))
        unit_id = clean(row.get("Unit_ID"))
        group_id = clean(row.get("Option_Group_ID"))
        option_id = clean(row.get("Option_ID"))
        option_name = clean(row.get("Option_Name"))
        if not lid or not unit_id or not group_id or not option_id or not option_name:
            fail(f"{army}: incomplete canonical loadout option identity")
        if lid in by_id:
            fail(f"{army}: duplicate Loadout_Option_ID {lid!r}")
        semantic_key = (unit_id, group_id, option_id)
        if semantic_key in {(v["Unit_ID"], v["Option_Group_ID"], v["Option_ID"]) for v in by_id.values()}:
            fail(f"{army}: duplicate semantic loadout option {semantic_key!r}")
        by_id[lid] = row
        group_options[(unit_id, group_id)].add(option_id)
        if clean(row.get("Default")).lower() in TRUE_VALUES:
            group_defaults[(unit_id, group_id)] += 1

    for group_key in group_options:
        if group_defaults[group_key] != 1:
            fail(f"{army}: {group_key!r} must have exactly one default option")

    for filename, rows in (
        ("Loadout_Weapons.csv", weapons),
        ("Loadout_Abilities.csv", abilities),
        ("Loadout_Points.csv", points),
        ("Loadout_Compatibility.csv", compatibility),
    ):
        for row in rows:
            lid = clean(row.get("Loadout_Option_ID"))
            if lid not in by_id:
                fail(f"{army}: {filename} references missing Loadout_Option_ID {lid!r}")

    for row in compatibility:
        lid = clean(row["Loadout_Option_ID"])
        parent = by_id[lid]
        required_group = clean(row.get("Required_Group_ID"))
        compatible_option = clean(row.get("Compatible_Option_ID"))
        if not required_group or compatible_option not in group_options.get((parent["Unit_ID"], required_group), set()):
            fail(
                f"{army}: compatibility for {lid!r} references unknown "
                f"{required_group}/{compatible_option}"
            )
    return by_id


def generate_compatibility(army, directory, tables):
    options, weapons, abilities, points, compatibility = tables
    by_id = validate_canonical(army, tables)

    def parent(lid):
        row = by_id[clean(lid)]
        return row["Unit_ID"], row["Option_Group_ID"], row["Option_ID"]

    compat_options = [
        [
            row["Unit_ID"], row["Option_Group_ID"], row["Group_Label"], row["Option_ID"],
            row["Option_Name"], row["Default"], row["Sort_Order"],
        ]
        for row in options
    ]
    compat_weapons = [
        [*parent(row["Loadout_Option_ID"]), row["Weapon_ID"], row["Weapon_Role"], row["Sort_Order"]]
        for row in weapons
    ]
    compat_abilities = [
        [*parent(row["Loadout_Option_ID"]), row["Ability_ID"], row["Sort_Order"]]
        for row in abilities
    ]
    compat_points = [
        [
            *parent(row["Loadout_Option_ID"]), row["Point_Option_ID"], row["Label"],
            row["Cost"], row["Sort_Order"],
        ]
        for row in points
    ]
    compat_compatibility = [
        [
            *parent(row["Loadout_Option_ID"]), row["Required_Group_ID"],
            row["Compatible_Option_ID"], row["Rule_Order"], row["Option_Order"],
        ]
        for row in compatibility
    ]
    compat_legacy_units = []

    write_csv(directory / "Unit_Loadout_Options.csv", COMPAT_OPTIONS_HEADER, compat_options)
    write_csv(directory / "Unit_Loadout_Weapons.csv", COMPAT_WEAPONS_HEADER, compat_weapons)
    write_csv(directory / "Unit_Loadout_Abilities.csv", COMPAT_ABILITIES_HEADER, compat_abilities)
    write_csv(directory / "Unit_Loadout_Points.csv", COMPAT_POINTS_HEADER, compat_points)
    write_csv(directory / "Unit_Loadout_Compatibility.csv", COMPAT_COMPAT_HEADER, compat_compatibility)
    write_csv(directory / "Unit_Loadout_Legacy_Units.csv", COMPAT_LEGACY_UNITS_HEADER, compat_legacy_units)

    return (
        [dict(zip(COMPAT_OPTIONS_HEADER, row)) for row in compat_options],
        [dict(zip(COMPAT_WEAPONS_HEADER, row)) for row in compat_weapons],
        [dict(zip(COMPAT_ABILITIES_HEADER, row)) for row in compat_abilities],
        [dict(zip(COMPAT_POINTS_HEADER, row)) for row in compat_points],
        [dict(zip(COMPAT_COMPAT_HEADER, row)) for row in compat_compatibility],
        [dict(zip(COMPAT_LEGACY_UNITS_HEADER, row)) for row in compat_legacy_units],
    )


def generate_legacy(army, directory, compat_tables):
    options, weapons, abilities, points, compatibility, _ = compat_tables

    option_keys = set()
    group_options = defaultdict(set)
    for row in options:
        key = (clean(row["Unit_ID"]), clean(row["Option_Group_ID"]), clean(row["Option_ID"]))
        option_keys.add(key)
        group_options[(key[0], key[1])].add(key[2])

    selected_weapons = defaultdict(list)
    preserved_weapons = defaultdict(list)
    ability_links = defaultdict(list)
    point_links = defaultdict(list)
    compatibility_links = defaultdict(list)

    for source_index, row in enumerate(weapons):
        key = (clean(row["Unit_ID"]), clean(row["Option_Group_ID"]), clean(row["Option_ID"]))
        record = (order_value(row["Sort_Order"]), source_index, clean(row["Weapon_ID"]))
        target = preserved_weapons if clean(row["Weapon_Role"]).upper() == "PRESERVE" else selected_weapons
        target[key].append(record)

    for source_index, row in enumerate(abilities):
        key = (clean(row["Unit_ID"]), clean(row["Option_Group_ID"]), clean(row["Option_ID"]))
        ability_links[key].append((order_value(row["Sort_Order"]), source_index, clean(row["Ability_ID"])))

    for source_index, row in enumerate(points):
        key = (clean(row["Unit_ID"]), clean(row["Option_Group_ID"]), clean(row["Option_ID"]))
        point_id = clean(row["Point_Option_ID"])
        sort_order = order_value(row["Sort_Order"])
        slot = 0
        if point_id.lower().startswith("point_"):
            try:
                slot = int(point_id.split("_", 1)[1])
            except ValueError:
                slot = 0
        if slot not in (1, 2):
            slot = sort_order if sort_order in (1, 2) else 0
        if slot not in (1, 2):
            fail(f"{army}: legacy Unit_Weapon_Options.csv cannot represent point slot {point_id!r} for {key!r}")
        if any(existing[0] == slot for existing in point_links[key]):
            fail(f"{army}: duplicate loadout point slot {slot} for {key!r}")
        point_links[key].append((slot, source_index, clean(row["Label"]), clean(row["Cost"])))

    for source_index, row in enumerate(compatibility):
        key = (clean(row["Unit_ID"]), clean(row["Option_Group_ID"]), clean(row["Option_ID"]))
        compatibility_links[key].append((
            order_value(row["Rule_Order"]) or 1,
            clean(row["Required_Group_ID"]),
            order_value(row["Option_Order"]) or 1,
            source_index,
            clean(row["Compatible_Option_ID"]),
        ))


    legacy_rows = []
    for option in options:
        key = (clean(option["Unit_ID"]), clean(option["Option_Group_ID"]), clean(option["Option_ID"]))
        selected = ", ".join(item[2] for item in sorted(selected_weapons[key]))
        preserved = ", ".join(item[2] for item in sorted(preserved_weapons[key]))
        granted = ", ".join(item[2] for item in sorted(ability_links[key]))
        aliases = ""
        point_slots = {slot: (label, cost) for slot, _, label, cost in point_links[key]}

        compat_groups = {}
        compat_order = []
        for rule_order, required_group, option_order, source_index, compatible_option in sorted(compatibility_links[key]):
            group_key = (rule_order, required_group)
            if group_key not in compat_groups:
                compat_groups[group_key] = []
                compat_order.append(group_key)
            compat_groups[group_key].append((option_order, source_index, compatible_option))
        compatible_with = ";".join(
            f"{required_group}=" + "|".join(item[2] for item in sorted(compat_groups[(rule_order, required_group)]))
            for rule_order, required_group in compat_order
        )

        point_1 = point_slots.get(1, ("", ""))
        point_2 = point_slots.get(2, ("", ""))
        legacy_rows.append([
            key[0], key[1], clean(option["Group_Label"]), key[2], clean(option["Option_Name"]),
            selected, granted, point_1[0], point_1[1], point_2[0], point_2[1],
            clean(option["Default"]), clean(option["Sort_Order"]), aliases, preserved, compatible_with,
        ])

    write_csv(directory / "Unit_Weapon_Options.csv", LEGACY_HEADER, legacy_rows)


def migrate_army(army):
    directory = ROOT / "data" / army
    tables = load_canonical(directory)
    compat_tables = generate_compatibility(army, directory, tables)
    generate_legacy(army, directory, compat_tables)
    options, weapons, abilities, points, compatibility = tables
    print(
        f"{army}: {len(options)} canonical Loadout_Option_ID rows -> compatibility tables "
        f"({len(weapons)} weapon links, {len(abilities)} ability links, {len(points)} point rows, "
        f"{len(compatibility)} compatibility rows)"
    )


def main():
    for army in ARMIES:
        migrate_army(army)
    print("canonical Loadout_Option_ID -> Unit_Loadout_* compatibility sync: OK")


if __name__ == "__main__":
    main()
