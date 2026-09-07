#!/usr/bin/env python3
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def remove_one(path, id_column, row_id):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        rows = list(reader)
    if not fieldnames or id_column not in fieldnames:
        raise SystemExit(f"{path}: missing {id_column}")
    kept = [row for row in rows if (row.get(id_column) or "").strip() != row_id]
    if len(rows) - len(kept) != 1:
        raise SystemExit(f"{path}: expected exactly one {row_id}, found {len(rows) - len(kept)}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(kept)


remove_one(ROOT / "data/nids/Unit_Abilities.csv", "Ability_ID", "LEADING_GENESTEALERS")
remove_one(ROOT / "data/nids/Abilities.csv", "Ability_ID", "LEADING_GENESTEALERS")
print("Removed LEADING_GENESTEALERS from Broodlord and deleted ability definition")
