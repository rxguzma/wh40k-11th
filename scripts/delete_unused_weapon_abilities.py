#!/usr/bin/env python3
"""Delete Weapon_Abilities rows for unused Weapon_Stats IDs.

A weapon is unused when its Weapon_ID is not referenced by Unit_Weapons.csv
or Loadout_Weapons.csv. Those leftover Ork clone profiles are the intended
target. Unit_Weapons and Loadout_Weapons are never modified.

Default is dry-run. Pass --apply to write files.
Pass --also-stats to delete the matching unused Weapon_Stats rows too.
"""

from __future__ import annotations

import argparse
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
    "Sort_Order",
]


def fail(message: str) -> None:
    raise SystemExit(message)


def read_dict_rows(path: Path, expected_header: list[str] | None = None) -> list[dict[str, str]]:
    if not path.exists():
        fail(f"missing file: {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if expected_header is not None and list(reader.fieldnames or []) != expected_header:
            fail(
                f"{path} header mismatch\n"
                f"expected: {expected_header!r}\n"
                f"actual:   {list(reader.fieldnames or [])!r}"
            )
        rows = list(reader)
    return [row for row in rows if any((value or "").strip() for value in row.values())]


def write_dict_rows(path: Path, header: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in header})


def referenced_weapon_ids(directory: Path) -> set[str]:
    used: set[str] = set()
    unit_weapons = directory / "Unit_Weapons.csv"
    loadout_weapons = directory / "Loadout_Weapons.csv"
    if unit_weapons.exists():
        for row in read_dict_rows(unit_weapons):
            weapon_id = (row.get("Weapon_ID") or "").strip()
            if weapon_id:
                used.add(weapon_id)
    if loadout_weapons.exists():
        for row in read_dict_rows(loadout_weapons):
            weapon_id = (row.get("Weapon_ID") or "").strip()
            if weapon_id:
                used.add(weapon_id)
    return used


def prune_army(army: str, apply: bool, also_stats: bool) -> None:
    directory = ROOT / "data" / army
    stats_path = directory / "Weapon_Stats.csv"
    abilities_path = directory / "Weapon_Abilities.csv"
    stats = read_dict_rows(stats_path, WEAPON_STATS_HEADER)
    abilities = read_dict_rows(abilities_path, WEAPON_ABILITIES_HEADER)
    used = referenced_weapon_ids(directory)
    unused = {(row.get("Weapon_ID") or "").strip() for row in stats}
    unused = {weapon_id for weapon_id in unused if weapon_id and weapon_id not in used}

    kept_abilities = [
        row for row in abilities if (row.get("Weapon_ID") or "").strip() not in unused
    ]
    removed_abilities = len(abilities) - len(kept_abilities)
    kept_stats = [
        row for row in stats if (row.get("Weapon_ID") or "").strip() not in unused
    ] if also_stats else stats
    removed_stats = len(stats) - len(kept_stats)

    print(
        f"{army}: unused weapons={len(unused)} "
        f"Weapon_Abilities {len(abilities)} -> {len(kept_abilities)} "
        f"(delete {removed_abilities})"
        + (
            f"; Weapon_Stats {len(stats)} -> {len(kept_stats)} (delete {removed_stats})"
            if also_stats
            else ""
        )
    )
    if unused:
        preview = ", ".join(sorted(unused)[:12])
        more = "" if len(unused) <= 12 else f" … +{len(unused) - 12} more"
        print(f"{army}: unused IDs: {preview}{more}")

    if not apply:
        return
    write_dict_rows(abilities_path, WEAPON_ABILITIES_HEADER, kept_abilities)
    if also_stats:
        write_dict_rows(stats_path, WEAPON_STATS_HEADER, kept_stats)
    print(f"{army}: wrote {abilities_path.relative_to(ROOT)}" + (
        f" and {stats_path.relative_to(ROOT)}" if also_stats else ""
    ))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--army", choices=ARMIES, action="append", dest="armies")
    parser.add_argument("--apply", action="store_true", help="Write CSV changes. Default is dry-run.")
    parser.add_argument(
        "--also-stats",
        action="store_true",
        help="Also delete unused Weapon_Stats rows after stripping their abilities.",
    )
    args = parser.parse_args()
    armies = tuple(args.armies) if args.armies else ARMIES
    if not args.apply:
        print("dry-run: no files will be written (pass --apply to delete)")
    for army in armies:
        prune_army(army, apply=args.apply, also_stats=args.also_stats)


if __name__ == "__main__":
    main()
