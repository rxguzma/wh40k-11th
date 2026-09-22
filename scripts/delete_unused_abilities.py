#!/usr/bin/env python3
"""Delete Abilities.csv rows that are not joined to a unit or loadout.

An ability is unused when its Ability_ID is absent from Unit_Abilities.csv
and Loadout_Abilities.csv. Only those Ability_ID columns are treated as
joins, so a unit named TECHMARINE does not keep an unused TECHMARINE ability.

Default is dry-run. Pass --apply to write Abilities.csv.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMIES = ("marines", "orks", "nids")
ABILITIES_HEADER = [
    "Ability_ID",
    "Ability Name",
    "Short_Description",
    "Long_Description",
    "Tags",
    "Visibility_ID",
    "Default_Active",
]


def fail(message: str) -> None:
    raise SystemExit(message)


def read_dict_rows(path: Path, expected_header: list[str] | None = None) -> list[dict[str, str]]:
    if not path.exists():
        return []
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
        writer = csv.DictWriter(
            handle,
            fieldnames=header,
            lineterminator="\n",
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in header})


def joined_ability_ids(directory: Path) -> set[str]:
    used: set[str] = set()
    for name in ("Unit_Abilities.csv", "Loadout_Abilities.csv"):
        for row in read_dict_rows(directory / name):
            ability_id = (row.get("Ability_ID") or "").strip()
            if ability_id:
                used.add(ability_id)
    return used


def prune_army(army: str, apply: bool) -> None:
    directory = ROOT / "data" / army
    path = directory / "Abilities.csv"
    rows = read_dict_rows(path, ABILITIES_HEADER)
    joined = joined_ability_ids(directory)
    unused = [row for row in rows if (row.get("Ability_ID") or "").strip() not in joined]
    unused_ids = sorted((row.get("Ability_ID") or "").strip() for row in unused)
    kept = [row for row in rows if (row.get("Ability_ID") or "").strip() in joined]
    print(f"{army}: unused abilities={len(unused)} Abilities {len(rows)} -> {len(kept)}")
    if unused_ids:
        print(f"{army}: unused IDs: {', '.join(unused_ids)}")
    if apply:
        write_dict_rows(path, ABILITIES_HEADER, kept)
        print(f"{army}: wrote {path.relative_to(ROOT)}")
    else:
        print("dry-run: no files will be written (pass --apply to delete)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--army", choices=ARMIES, action="append")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    armies = args.army or list(ARMIES)
    if not args.apply:
        print("dry-run: no files will be written (pass --apply to delete)")
    for army in armies:
        prune_army(army, args.apply)


if __name__ == "__main__":
    main()
