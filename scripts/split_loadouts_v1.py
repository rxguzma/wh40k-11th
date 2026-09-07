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
OPTIONS_HEADER = [
    "Unit_ID", "Option_Group_ID", "Group_Label", "Option_ID", "Option_Name",
    "Default", "Sort_Order",
]
WEAPONS_HEADER = [
    "Unit_ID", "Option_Group_ID", "Option_ID", "Weapon_ID", "Weapon_Role", "Sort_Order",
]
ABILITIES_HEADER = [
    "Unit_ID", "Option_Group_ID", "Option_ID", "Ability_ID", "Sort_Order",
]
POINTS_HEADER = [
    "Unit_ID", "Option_Group_ID", "Option_ID", "Point_Option_ID", "Label", "Cost", "Sort_Order",
]
COMPAT_HEADER = [
    "Unit_ID", "Option_Group_ID", "Option_ID", "Required_Group_ID",
    "Compatible_Option_ID", "Rule_Order", "Option_Order",
]
LEGACY_UNITS_HEADER = [
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


def option_key(row):
    return (clean(row.get("Unit_ID")), clean(row.get("Option_Group_ID")), clean(row.get("Option_ID")))


def migrate_army(army):
    directory = ROOT / "data" / army
    options = read_dicts(directory / "Unit_Loadout_Options.csv", OPTIONS_HEADER)
    weapons = read_dicts(directory / "Unit_Loadout_Weapons.csv", WEAPONS_HEADER)
    abilities = read_dicts(directory / "Unit_Loadout_Abilities.csv", ABILITIES_HEADER)
    points = read_dicts(directory / "Unit_Loadout_Points.csv", POINTS_HEADER)
    compatibility = read_dicts(directory / "Unit_Loadout_Compatibility.csv", COMPAT_HEADER)
    legacy_units = read_dicts(directory / "Unit_Loadout_Legacy_Units.csv", LEGACY_UNITS_HEADER)

    option_keys = set()
    group_defaults = defaultdict(int)
    group_options = defaultdict(set)
    for row in options:
        unit_id, group_id, option_id = option_key(row)
        option_name = clean(row.get("Option_Name"))
        if not unit_id or not group_id or not option_id or not option_name:
            fail(f"{army}: incomplete normalized loadout option identity")
        key = (unit_id, group_id, option_id)
        if key in option_keys:
            fail(f"{army}: duplicate normalized loadout option {key!r}")
        option_keys.add(key)
        group_options[(unit_id, group_id)].add(option_id)
        if clean(row.get("Default")).lower() in TRUE_VALUES:
            group_defaults[(unit_id, group_id)] += 1

    for group_key in group_options:
        if group_defaults[group_key] != 1:
            fail(f"{army}: {group_key!r} must have exactly one default option")

    selected_weapons = defaultdict(list)
    preserved_weapons = defaultdict(list)
    ability_links = defaultdict(list)
    point_links = defaultdict(list)
    compatibility_links = defaultdict(list)
    legacy_links = defaultdict(list)

    for source_index, row in enumerate(weapons):
        key = option_key(row)
        if key not in option_keys:
            fail(f"{army}: loadout weapon references missing option {key!r}")
        weapon_id = clean(row.get("Weapon_ID"))
        role = clean(row.get("Weapon_Role")).upper()
        if not weapon_id or role not in {"SELECTED", "PRESERVE"}:
            fail(f"{army}: invalid loadout weapon row for {key!r}")
        record = (order_value(row.get("Sort_Order")), source_index, weapon_id)
        (preserved_weapons if role == "PRESERVE" else selected_weapons)[key].append(record)

    for source_index, row in enumerate(abilities):
        key = option_key(row)
        if key not in option_keys:
            fail(f"{army}: loadout ability references missing option {key!r}")
        ability_id = clean(row.get("Ability_ID"))
        if not ability_id:
            fail(f"{army}: blank loadout Ability_ID for {key!r}")
        ability_links[key].append((order_value(row.get("Sort_Order")), source_index, ability_id))

    for source_index, row in enumerate(points):
        key = option_key(row)
        if key not in option_keys:
            fail(f"{army}: loadout point references missing option {key!r}")
        point_id = clean(row.get("Point_Option_ID"))
        sort_order = order_value(row.get("Sort_Order"))
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
        point_links[key].append((slot, source_index, clean(row.get("Label")), clean(row.get("Cost"))))

    for source_index, row in enumerate(compatibility):
        key = option_key(row)
        if key not in option_keys:
            fail(f"{army}: compatibility references missing option {key!r}")
        required_group = clean(row.get("Required_Group_ID"))
        compatible_option = clean(row.get("Compatible_Option_ID"))
        if not required_group or compatible_option not in group_options.get((key[0], required_group), set()):
            fail(f"{army}: compatibility for {key!r} references unknown {required_group}/{compatible_option}")
        compatibility_links[key].append((
            order_value(row.get("Rule_Order")) or 1,
            required_group,
            order_value(row.get("Option_Order")) or 1,
            source_index,
            compatible_option,
        ))

    for source_index, row in enumerate(legacy_units):
        key = option_key(row)
        if key not in option_keys:
            fail(f"{army}: legacy-unit alias references missing option {key!r}")
        legacy_id = clean(row.get("Legacy_Unit_ID"))
        if not legacy_id:
            fail(f"{army}: blank Legacy_Unit_ID for {key!r}")
        legacy_links[key].append((order_value(row.get("Sort_Order")), source_index, legacy_id))

    legacy_rows = []
    for option in options:
        key = option_key(option)
        selected = ", ".join(item[2] for item in sorted(selected_weapons[key]))
        preserved = ", ".join(item[2] for item in sorted(preserved_weapons[key]))
        granted = ", ".join(item[2] for item in sorted(ability_links[key]))
        aliases = ", ".join(item[2] for item in sorted(legacy_links[key]))

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
            key[0], key[1], clean(option.get("Group_Label")), key[2], clean(option.get("Option_Name")),
            selected, granted, point_1[0], point_1[1], point_2[0], point_2[1],
            clean(option.get("Default")), clean(option.get("Sort_Order")), aliases, preserved, compatible_with,
        ])

    write_csv(directory / "Unit_Weapon_Options.csv", LEGACY_HEADER, legacy_rows)
    print(
        f"{army}: {len(options)} normalized options -> legacy Unit_Weapon_Options.csv "
        f"({len(weapons)} weapon links, {len(abilities)} ability links, {len(points)} point rows, "
        f"{len(compatibility)} compatibility rows, {len(legacy_units)} legacy-unit aliases)"
    )


def main():
    for army in ARMIES:
        migrate_army(army)
    print("normalized loadout compatibility sync: OK")


if __name__ == "__main__":
    main()
