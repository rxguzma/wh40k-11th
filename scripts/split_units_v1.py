#!/usr/bin/env python3
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMIES = ("marines", "orks", "nids")

UNITS_HEADER = [
    "Unit_ID",
    "Unit Name",
    "Ability_IDs",
    "Core_Ability_IDs",
    "Weapon_IDs",
    'M"',
    "T",
    "SV",
    "W",
    "LD",
    "OC",
    "Keywords",
    "Hyperlink",
]
for index in range(1, 9):
    UNITS_HEADER.extend([f"Points_Label_{index}", f"Points_Cost_{index}"])

UNIT_ABILITIES_HEADER = ["Unit_ID", "Ability_ID", "Ability_Type"]
UNIT_WEAPONS_HEADER = ["Unit_ID", "Weapon_ID"]
UNIT_POINTS_HEADER = ["Unit_ID", "Point_Option_ID", "Label", "Cost", "Sort_Order"]


def fail(message):
    raise SystemExit(message)


def read_dict_rows(path, expected_header):
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


def write_units(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=UNITS_HEADER, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def add_unique(mapping, key, value, label, army):
    values = mapping.setdefault(key, [])
    if value in values:
        fail(f"{army}: duplicate {label} relationship {(key, value)!r}")
    values.append(value)


def point_slot(row, army):
    option_id = (row.get("Point_Option_ID") or "").strip()
    sort_text = (row.get("Sort_Order") or "").strip()

    slot = 0
    if option_id.lower().startswith("point_"):
        suffix = option_id[6:]
        if suffix.isdigit():
            slot = int(suffix)
    if not 1 <= slot <= 8:
        try:
            slot = int(sort_text)
        except ValueError:
            slot = 0
    if not 1 <= slot <= 8:
        fail(f"{army}: invalid point slot for {row!r}")
    return slot


def sync_army(army):
    directory = ROOT / "data" / army
    units_path = directory / "Units.csv"
    units = read_dict_rows(units_path, UNITS_HEADER)
    abilities = read_dict_rows(directory / "Unit_Abilities.csv", UNIT_ABILITIES_HEADER)
    weapons = read_dict_rows(directory / "Unit_Weapons.csv", UNIT_WEAPONS_HEADER)
    points = read_dict_rows(directory / "Unit_Points.csv", UNIT_POINTS_HEADER)

    unit_ids = []
    unit_id_set = set()
    for line_no, unit in enumerate(units, start=2):
        unit_id = (unit.get("Unit_ID") or "").strip()
        if not unit_id:
            fail(f"{army}: blank Unit_ID at Units.csv line {line_no}")
        if unit_id in unit_id_set:
            fail(f"{army}: duplicate Unit_ID {unit_id!r}")
        unit_id_set.add(unit_id)
        unit_ids.append(unit_id)

    ability_map = {}
    core_ability_map = {}
    weapon_map = {}
    point_map = {}

    for line_no, row in enumerate(abilities, start=2):
        unit_id = (row.get("Unit_ID") or "").strip()
        ability_id = (row.get("Ability_ID") or "").strip()
        ability_type = (row.get("Ability_Type") or "").strip().upper()
        if unit_id not in unit_id_set:
            fail(f"{army}: Unit_Abilities line {line_no} references missing Unit_ID {unit_id!r}")
        if not ability_id:
            fail(f"{army}: blank Ability_ID in Unit_Abilities line {line_no}")
        if ability_type == "ABILITY":
            add_unique(ability_map, unit_id, ability_id, "unit ability", army)
        elif ability_type == "CORE_ABILITY":
            add_unique(core_ability_map, unit_id, ability_id, "unit core ability", army)
        else:
            fail(f"{army}: unsupported Ability_Type {ability_type!r} in Unit_Abilities line {line_no}")

    for line_no, row in enumerate(weapons, start=2):
        unit_id = (row.get("Unit_ID") or "").strip()
        weapon_id = (row.get("Weapon_ID") or "").strip()
        if unit_id not in unit_id_set:
            fail(f"{army}: Unit_Weapons line {line_no} references missing Unit_ID {unit_id!r}")
        if not weapon_id:
            fail(f"{army}: blank Weapon_ID in Unit_Weapons line {line_no}")
        add_unique(weapon_map, unit_id, weapon_id, "unit weapon", army)

    for line_no, row in enumerate(points, start=2):
        unit_id = (row.get("Unit_ID") or "").strip()
        if unit_id not in unit_id_set:
            fail(f"{army}: Unit_Points line {line_no} references missing Unit_ID {unit_id!r}")
        slot = point_slot(row, army)
        slots = point_map.setdefault(unit_id, {})
        if slot in slots:
            fail(f"{army}: duplicate Unit_Points slot {slot} for {unit_id!r}")
        slots[slot] = {
            "label": row.get("Label") or "",
            "cost": row.get("Cost") or "",
        }

    changed = False
    for unit in units:
        unit_id = (unit.get("Unit_ID") or "").strip()
        next_values = {
            "Ability_IDs": ", ".join(ability_map.get(unit_id, [])),
            "Core_Ability_IDs": ", ".join(core_ability_map.get(unit_id, [])),
            "Weapon_IDs": ", ".join(weapon_map.get(unit_id, [])),
        }
        slots = point_map.get(unit_id, {})
        for index in range(1, 9):
            point = slots.get(index)
            next_values[f"Points_Label_{index}"] = point["label"] if point else ""
            next_values[f"Points_Cost_{index}"] = point["cost"] if point else ""

        for column, value in next_values.items():
            if (unit.get(column) or "") != value:
                unit[column] = value
                changed = True

    if changed:
        write_units(units_path, units)

    print(
        f"{army}: {len(units)} units <- "
        f"{len(abilities)} normalized ability links, "
        f"{len(weapons)} normalized weapon links, "
        f"{len(points)} normalized point options "
        f"({'updated' if changed else 'current'})"
    )


def main():
    for army in ARMIES:
        sync_army(army)
    print("normalized unit compatibility sync: OK")


if __name__ == "__main__":
    main()
