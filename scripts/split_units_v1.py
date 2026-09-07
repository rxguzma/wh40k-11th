#!/usr/bin/env python3
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMIES = ("marines", "orks", "nids")

PROFILE_HEADER = [
    "Unit_ID",
    "Unit Name",
    'M"',
    "T",
    "SV",
    "W",
    "LD",
    "OC",
    "Keywords",
    "Hyperlink",
]

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
    profiles = read_dict_rows(directory / "Unit_Profiles.csv", PROFILE_HEADER)
    abilities = read_dict_rows(directory / "Unit_Abilities.csv", UNIT_ABILITIES_HEADER)
    weapons = read_dict_rows(directory / "Unit_Weapons.csv", UNIT_WEAPONS_HEADER)
    points = read_dict_rows(directory / "Unit_Points.csv", UNIT_POINTS_HEADER)

    unit_id_set = set()
    for line_no, profile in enumerate(profiles, start=2):
        unit_id = (profile.get("Unit_ID") or "").strip()
        if not unit_id:
            fail(f"{army}: blank Unit_ID at Unit_Profiles.csv line {line_no}")
        if unit_id in unit_id_set:
            fail(f"{army}: duplicate Unit_ID {unit_id!r} in Unit_Profiles.csv")
        unit_id_set.add(unit_id)

    ability_map = {}
    core_ability_map = {}
    weapon_map = {}
    point_map = {}

    for line_no, row in enumerate(abilities, start=2):
        unit_id = (row.get("Unit_ID") or "").strip()
        ability_id = (row.get("Ability_ID") or "").strip()
        ability_type = (row.get("Ability_Type") or "").strip().upper()
        if unit_id not in unit_id_set:
            fail(f"{army}: Unit_Abilities line {line_no} references missing Unit_Profile {unit_id!r}")
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
            fail(f"{army}: Unit_Weapons line {line_no} references missing Unit_Profile {unit_id!r}")
        if not weapon_id:
            fail(f"{army}: blank Weapon_ID in Unit_Weapons line {line_no}")
        add_unique(weapon_map, unit_id, weapon_id, "unit weapon", army)

    for line_no, row in enumerate(points, start=2):
        unit_id = (row.get("Unit_ID") or "").strip()
        if unit_id not in unit_id_set:
            fail(f"{army}: Unit_Points line {line_no} references missing Unit_Profile {unit_id!r}")
        slot = point_slot(row, army)
        slots = point_map.setdefault(unit_id, {})
        if slot in slots:
            fail(f"{army}: duplicate Unit_Points slot {slot} for {unit_id!r}")
        slots[slot] = {"label": row.get("Label") or "", "cost": row.get("Cost") or ""}

    units = []
    for profile in profiles:
        unit_id = (profile.get("Unit_ID") or "").strip()
        unit = {column: "" for column in UNITS_HEADER}
        for column in PROFILE_HEADER:
            unit[column] = profile.get(column) or ""
        unit["Ability_IDs"] = ", ".join(ability_map.get(unit_id, []))
        unit["Core_Ability_IDs"] = ", ".join(core_ability_map.get(unit_id, []))
        unit["Weapon_IDs"] = ", ".join(weapon_map.get(unit_id, []))
        for index, point in point_map.get(unit_id, {}).items():
            unit[f"Points_Label_{index}"] = point["label"]
            unit[f"Points_Cost_{index}"] = point["cost"]
        units.append(unit)

    current = read_dict_rows(units_path, UNITS_HEADER) if units_path.exists() else []
    changed = current != units
    if changed:
        write_units(units_path, units)

    print(
        f"{army}: {len(units)} generated units <- Unit_Profiles + "
        f"{len(abilities)} ability links, {len(weapons)} weapon links, {len(points)} point options "
        f"({'updated' if changed else 'current'})"
    )

def main():
    for army in ARMIES:
        sync_army(army)
    print("authoritative Unit_Profiles -> legacy Units compatibility sync: OK")


if __name__ == "__main__":
    main()
