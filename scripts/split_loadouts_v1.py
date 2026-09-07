#!/usr/bin/env python3
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMIES = ("marines", "orks", "nids")

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


def split_ids(value):
    return [part.strip() for part in (value or "").split(",") if part.strip()]


def read_legacy(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != LEGACY_HEADER:
            fail(
                f"{path.relative_to(ROOT)} header mismatch\n"
                f"expected: {LEGACY_HEADER!r}\n"
                f"actual:   {reader.fieldnames!r}"
            )
        rows = list(reader)
    return [row for row in rows if any((value or "").strip() for value in row.values())]


def write_csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def parse_compatibility(raw, army, unit_id, group_id, option_id):
    result = []
    for rule_order, raw_rule in enumerate((raw or "").split(";"), start=1):
        rule = raw_rule.strip()
        if not rule:
            continue
        sep = "=" if "=" in rule else (":" if ":" in rule else None)
        if not sep:
            fail(f"{army} {unit_id}/{group_id}/{option_id}: invalid Compatible_With rule {rule!r}")
        required_group, option_text = rule.split(sep, 1)
        required_group = required_group.strip()
        allowed = [part.strip() for part in option_text.split("|") if part.strip()]
        if not required_group or not allowed:
            fail(f"{army} {unit_id}/{group_id}/{option_id}: incomplete Compatible_With rule {rule!r}")
        for option_order, compatible_option in enumerate(allowed, start=1):
            result.append([
                unit_id, group_id, option_id, required_group,
                compatible_option, str(rule_order), str(option_order),
            ])
    return result


def migrate_army(army):
    directory = ROOT / "data" / army
    legacy_rows = read_legacy(directory / "Unit_Weapon_Options.csv")

    option_rows = []
    weapon_rows = []
    ability_rows = []
    point_rows = []
    compatibility_rows = []
    legacy_unit_rows = []

    option_keys = set()
    group_defaults = {}

    for source_line, row in enumerate(legacy_rows, start=2):
        unit_id = (row.get("Unit_ID") or "").strip()
        group_id = (row.get("Option_Group_ID") or "").strip()
        option_id = (row.get("Option_ID") or "").strip()
        option_name = (row.get("Option_Name") or "").strip()
        group_label = (row.get("Group_Label") or "").strip()
        default = (row.get("Default") or "").strip()
        sort_order = (row.get("Sort_Order") or "").strip()

        if not unit_id or not group_id or not option_id or not option_name:
            fail(f"{army}: incomplete option identity at Unit_Weapon_Options.csv line {source_line}")
        key = (unit_id, group_id, option_id)
        if key in option_keys:
            fail(f"{army}: duplicate loadout option {key!r}")
        option_keys.add(key)
        option_rows.append([unit_id, group_id, group_label, option_id, option_name, default, sort_order])

        if default.lower() in {"true", "1", "yes", "y"}:
            group_key = (unit_id, group_id)
            if group_key in group_defaults:
                fail(f"{army}: multiple defaults for {unit_id}/{group_id}")
            group_defaults[group_key] = option_id

        for index, weapon_id in enumerate(split_ids(row.get("Weapon_IDs")), start=1):
            weapon_rows.append([unit_id, group_id, option_id, weapon_id, "SELECTED", str(index)])
        for index, weapon_id in enumerate(split_ids(row.get("Preserve_Weapon_IDs")), start=1):
            weapon_rows.append([unit_id, group_id, option_id, weapon_id, "PRESERVE", str(index)])
        for index, ability_id in enumerate(split_ids(row.get("Ability_IDs")), start=1):
            ability_rows.append([unit_id, group_id, option_id, ability_id, str(index)])
        for index in range(1, 3):
            label = (row.get(f"Points_Label_{index}") or "").strip()
            cost = (row.get(f"Points_Cost_{index}") or "").strip()
            if not label and not cost:
                continue
            point_rows.append([
                unit_id, group_id, option_id, f"point_{index}", label, cost, str(index)
            ])
        compatibility_rows.extend(
            parse_compatibility(row.get("Compatible_With"), army, unit_id, group_id, option_id)
        )
        for index, legacy_unit_id in enumerate(split_ids(row.get("Legacy_Unit_IDs")), start=1):
            legacy_unit_rows.append([unit_id, group_id, option_id, legacy_unit_id, str(index)])

    groups = {(row[0], row[1]) for row in option_rows}
    missing_defaults = sorted(group for group in groups if group not in group_defaults)
    if missing_defaults:
        fail(f"{army}: option groups without a default: {missing_defaults!r}")

    write_csv(directory / "Unit_Loadout_Options.csv", OPTIONS_HEADER, option_rows)
    write_csv(directory / "Unit_Loadout_Weapons.csv", WEAPONS_HEADER, weapon_rows)
    write_csv(directory / "Unit_Loadout_Abilities.csv", ABILITIES_HEADER, ability_rows)
    write_csv(directory / "Unit_Loadout_Points.csv", POINTS_HEADER, point_rows)
    write_csv(directory / "Unit_Loadout_Compatibility.csv", COMPAT_HEADER, compatibility_rows)
    write_csv(directory / "Unit_Loadout_Legacy_Units.csv", LEGACY_UNITS_HEADER, legacy_unit_rows)

    print(
        f"{army}: {len(option_rows)} options -> "
        f"{len(weapon_rows)} weapon links, {len(ability_rows)} ability links, "
        f"{len(point_rows)} point rows, {len(compatibility_rows)} compatibility rows, "
        f"{len(legacy_unit_rows)} legacy-unit aliases"
    )


def main():
    for army in ARMIES:
        migrate_army(army)
    print("loadout split migration: OK")


if __name__ == "__main__":
    main()
