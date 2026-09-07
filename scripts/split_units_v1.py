#!/usr/bin/env python3
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMIES = ("marines", "orks", "nids")

EXPECTED_UNITS_HEADER = [
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
    EXPECTED_UNITS_HEADER.extend([f"Points_Label_{index}", f"Points_Cost_{index}"])

UNIT_ABILITIES_HEADER = ["Unit_ID", "Ability_ID", "Ability_Type"]
UNIT_WEAPONS_HEADER = ["Unit_ID", "Weapon_ID"]
UNIT_POINTS_HEADER = ["Unit_ID", "Point_Option_ID", "Label", "Cost", "Sort_Order"]


def fail(message):
    raise SystemExit(message)


def split_ids(value):
    return [part.strip() for part in (value or "").split(",") if part.strip()]


def read_units(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != EXPECTED_UNITS_HEADER:
            fail(
                f"{path.relative_to(ROOT)} header mismatch\n"
                f"expected: {EXPECTED_UNITS_HEADER!r}\n"
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


def require_unique(values, label, army):
    seen = set()
    for value in values:
        if value in seen:
            fail(f"{army}: duplicate {label} {value!r}")
        seen.add(value)


def migrate_army(army):
    directory = ROOT / "data" / army
    units = read_units(directory / "Units.csv")

    unit_ids = []
    ability_rows = []
    weapon_rows = []
    point_rows = []

    ability_keys = set()
    weapon_keys = set()
    point_keys = set()

    for source_line, unit in enumerate(units, start=2):
        unit_id = (unit.get("Unit_ID") or "").strip()
        if not unit_id:
            fail(f"{army}: blank Unit_ID at Units.csv line {source_line}")
        unit_ids.append(unit_id)

        for ability_type, source_column in (
            ("ABILITY", "Ability_IDs"),
            ("CORE_ABILITY", "Core_Ability_IDs"),
        ):
            for ability_id in split_ids(unit.get(source_column)):
                key = (unit_id, ability_type, ability_id)
                if key in ability_keys:
                    fail(f"{army}: duplicate unit ability relationship {key!r}")
                ability_keys.add(key)
                ability_rows.append([unit_id, ability_id, ability_type])

        for weapon_id in split_ids(unit.get("Weapon_IDs")):
            key = (unit_id, weapon_id)
            if key in weapon_keys:
                fail(f"{army}: duplicate unit weapon relationship {key!r}")
            weapon_keys.add(key)
            weapon_rows.append([unit_id, weapon_id])

        for index in range(1, 9):
            label = (unit.get(f"Points_Label_{index}") or "").strip()
            cost = (unit.get(f"Points_Cost_{index}") or "").strip()
            if not label and not cost:
                continue
            option_id = f"point_{index}"
            key = (unit_id, option_id)
            if key in point_keys:
                fail(f"{army}: duplicate unit point relationship {key!r}")
            point_keys.add(key)
            point_rows.append([unit_id, option_id, label, cost, str(index)])

    require_unique(unit_ids, "Unit_ID", army)

    write_csv(directory / "Unit_Abilities.csv", UNIT_ABILITIES_HEADER, ability_rows)
    write_csv(directory / "Unit_Weapons.csv", UNIT_WEAPONS_HEADER, weapon_rows)
    write_csv(directory / "Unit_Points.csv", UNIT_POINTS_HEADER, point_rows)

    print(
        f"{army}: {len(units)} units -> "
        f"{len(ability_rows)} unit abilities, "
        f"{len(weapon_rows)} unit weapons, "
        f"{len(point_rows)} unit point options"
    )


def main():
    for army in ARMIES:
        migrate_army(army)
    print("unit relationship split migration: OK")


if __name__ == "__main__":
    main()
