#!/usr/bin/env python3
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMIES = ("marines", "orks", "nids")

WEAPON_STATS_HEADER = ["Weapon_ID", "Weapon Name", 'R"', "A", "WS", "St", "AP", "D", "Weapon Abilities"]
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


def write_stats(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=WEAPON_STATS_HEADER, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def render_ability(row):
    ability_type = (row.get("Ability_Type") or "").strip()
    target = (row.get("Target") or "").strip()
    value = (row.get("Value") or "").strip()
    condition = (row.get("Condition") or "").strip()

    if not ability_type:
        fail(f"blank Ability_Type for {row!r}")
    if ability_type == "NONE":
        if target or value or condition:
            fail(f"NONE ability cannot have Target/Value/Condition: {row!r}")
        return "-"

    if ability_type == "ANTI":
        if not target or not value:
            fail(f"ANTI requires Target and Value: {row!r}")
        text = f"ANTI-{target} {value}"
    else:
        if target:
            fail(f"Target is only supported for ANTI weapon abilities: {row!r}")
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
                fail(f"{army}: first weapon ability for {weapon_id!r} must have blank Separator_Before")
        elif not separator.startswith(","):
            fail(f"{army}: non-first weapon ability for {weapon_id!r} must use a comma separator")
        output += separator + render_ability(row)
    return output


def sync_army(army):
    directory = ROOT / "data" / army
    stats_path = directory / "Weapon_Stats.csv"
    abilities_path = directory / "Weapon_Abilities.csv"
    stats = read_dict_rows(stats_path, WEAPON_STATS_HEADER)
    abilities = read_dict_rows(abilities_path, WEAPON_ABILITIES_HEADER)

    weapon_ids = set()
    for line_no, row in enumerate(stats, start=2):
        weapon_id = (row.get("Weapon_ID") or "").strip()
        if not weapon_id:
            fail(f"{army}: blank Weapon_ID in Weapon_Stats.csv line {line_no}")
        if weapon_id in weapon_ids:
            fail(f"{army}: duplicate Weapon_ID {weapon_id!r}")
        weapon_ids.add(weapon_id)

    grouped = {}
    seen_ids = set()
    seen_order = set()
    for line_no, row in enumerate(abilities, start=2):
        weapon_id = (row.get("Weapon_ID") or "").strip()
        relation_id = (row.get("Weapon_Ability_ID") or "").strip()
        if weapon_id not in weapon_ids:
            fail(f"{army}: Weapon_Abilities line {line_no} references missing Weapon_ID {weapon_id!r}")
        if not relation_id:
            fail(f"{army}: blank Weapon_Ability_ID in Weapon_Abilities line {line_no}")
        if relation_id in seen_ids:
            fail(f"{army}: duplicate Weapon_Ability_ID {relation_id!r}")
        seen_ids.add(relation_id)
        try:
            sort_order = int((row.get("Sort_Order") or "").strip())
        except ValueError:
            fail(f"{army}: invalid Sort_Order in Weapon_Abilities line {line_no}")
        if sort_order < 1:
            fail(f"{army}: Sort_Order must be >= 1 in Weapon_Abilities line {line_no}")
        order_key = (weapon_id, sort_order)
        if order_key in seen_order:
            fail(f"{army}: duplicate Weapon_Abilities Sort_Order {sort_order} for {weapon_id!r}")
        seen_order.add(order_key)
        grouped.setdefault(weapon_id, []).append((sort_order, row))

    changed = False
    for row in stats:
        weapon_id = (row.get("Weapon_ID") or "").strip()
        next_value = render_group(grouped.get(weapon_id, []), army, weapon_id)
        if (row.get("Weapon Abilities") or "") != next_value:
            row["Weapon Abilities"] = next_value
            changed = True

    if changed:
        write_stats(stats_path, stats)

    print(
        f"{army}: {len(abilities)} authoritative weapon ability rows -> "
        f"{len(stats)} Weapon_Stats compatibility rows "
        f"({'updated' if changed else 'current'})"
    )


def main():
    for army in ARMIES:
        sync_army(army)
    print("authoritative Weapon_Abilities -> Weapon_Stats compatibility sync: OK")


if __name__ == "__main__":
    main()
