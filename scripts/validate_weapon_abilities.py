#!/usr/bin/env python3
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMIES = ("marines", "orks", "nids")

WEAPON_STATS_HEADER = ["Weapon_ID", "Weapon Name", 'R"', "A", "WS", "St", "AP", "D"]
WEAPON_ABILITIES_HEADER = [
    "Weapon_ID",
    "Weapon_Ability_ID",
    "Ability_Type",
    "Target",
    "Value",
    "Condition",
    "Separator_Before",
    "Sort_Order",
]


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


def render(row):
    ability_type = (row.get("Ability_Type") or "").strip()
    target = (row.get("Target") or "").strip()
    value = (row.get("Value") or "").strip()
    condition = (row.get("Condition") or "").strip()

    if not ability_type:
        fail(f"blank Ability_Type: {row!r}")
    if ability_type == "NONE":
        if target or value or condition:
            fail(f"NONE cannot have Target/Value/Condition: {row!r}")
        return "-"
    if ability_type == "ANTI":
        if not target or not value:
            fail(f"ANTI requires Target and Value: {row!r}")
        text = f"ANTI-{target} {value}"
    else:
        if target:
            fail(f"Target is only valid for ANTI: {row!r}")
        text = ability_type
        if value:
            text += f" {value}"
    if condition:
        text += f": {condition}"
    return text


def render_group(rows, army, weapon_id):
    output = ""
    for index, (_, row) in enumerate(sorted(rows, key=lambda pair: pair[0])):
        separator = row.get("Separator_Before") or ""
        if index == 0:
            if separator:
                fail(f"{army}: first ability for {weapon_id!r} has nonblank Separator_Before")
        elif not separator.startswith(","):
            fail(f"{army}: non-first ability for {weapon_id!r} must use a comma separator")
        output += separator + render(row)
    return output


def validate_army(army):
    directory = ROOT / "data" / army
    stats = read_dict_rows(directory / "Weapon_Stats.csv", WEAPON_STATS_HEADER)
    abilities = read_dict_rows(directory / "Weapon_Abilities.csv", WEAPON_ABILITIES_HEADER)

    weapon_ids = set()
    for line_no, row in enumerate(stats, start=2):
        weapon_id = (row.get("Weapon_ID") or "").strip()
        if not weapon_id:
            fail(f"{army}: blank Weapon_ID in Weapon_Stats line {line_no}")
        if weapon_id in weapon_ids:
            fail(f"{army}: duplicate Weapon_ID {weapon_id!r}")
        weapon_ids.add(weapon_id)

    relation_ids = set()
    sort_keys = set()
    grouped = {}
    for line_no, row in enumerate(abilities, start=2):
        weapon_id = (row.get("Weapon_ID") or "").strip()
        relation_id = (row.get("Weapon_Ability_ID") or "").strip()
        if weapon_id not in weapon_ids:
            fail(f"{army}: Weapon_Abilities line {line_no} references missing Weapon_ID {weapon_id!r}")
        if not relation_id:
            fail(f"{army}: blank Weapon_Ability_ID line {line_no}")
        if relation_id in relation_ids:
            fail(f"{army}: duplicate Weapon_Ability_ID {relation_id!r}")
        relation_ids.add(relation_id)
        try:
            sort_order = int((row.get("Sort_Order") or "").strip())
        except ValueError:
            fail(f"{army}: invalid Sort_Order line {line_no}")
        if sort_order < 1:
            fail(f"{army}: Sort_Order must be >= 1 line {line_no}")
        sort_key = (weapon_id, sort_order)
        if sort_key in sort_keys:
            fail(f"{army}: duplicate Sort_Order {sort_order} for {weapon_id!r}")
        sort_keys.add(sort_key)
        render(row)
        grouped.setdefault(weapon_id, []).append((sort_order, row))

    for weapon_id, rows in grouped.items():
        render_group(rows, army, weapon_id)

    print(f"{army}: weapon abilities OK — {len(abilities)} normalized rows across {len(grouped)} weapons")


def main():
    for army in ARMIES:
        validate_army(army)
    print("authoritative weapon ability validation: OK")


if __name__ == "__main__":
    main()
