#!/usr/bin/env python3
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "data" / "CSV_SCHEMA.csv"
HEADER = ["Scope", "File", "Column_Order", "Column_Name", "Required", "Notes"]
ROWS = [
    ["army", "Effects.csv", "1", "Effect_ID", "YES", "Stable unique effect key."],
    ["army", "Effects.csv", "2", "Source_Type", "YES", "ABILITY or ENHANCEMENT."],
    ["army", "Effects.csv", "3", "Source_ID", "YES", "Foreign key to Ability_ID or Enhancement_ID according to Source_Type."],
    ["army", "Effects.csv", "4", "Effect_Type", "YES", "STAT, POINTS_PER_MODEL, or KEYWORD."],
    ["army", "Effects.csv", "5", "Target", "YES", "Execution target; currently UNIT."],
    ["army", "Effects.csv", "6", "Stat", "YES", "M/T/SV/W/LD/OC, PTS, or KEYWORD according to Effect_Type."],
    ["army", "Effects.csv", "7", "Operation", "YES", "ADD, SET, or REMOVE according to Effect_Type."],
    ["army", "Effects.csv", "8", "Value", "YES", "Machine-readable effect value."],
    ["army", "Effects.csv", "9", "Display_Tag", "YES", "Exact visible compatibility tag preserved for Short Description badge presentation and older HTML."],
    ["army", "Effects.csv", "10", "Sort_Order", "YES", "Effect order within its source."],
]


def main():
    with PATH.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    if not rows or rows[0] != HEADER:
        raise SystemExit(f"unexpected CSV_SCHEMA.csv header: {rows[0] if rows else None!r}")
    existing = {(row[0], row[1], row[3]) for row in rows[1:] if len(row) >= 4}
    added = 0
    for row in ROWS:
        key = (row[0], row[1], row[3])
        if key not in existing:
            rows.append(row)
            existing.add(key)
            added += 1
    if added:
        with PATH.open("w", encoding="utf-8", newline="") as handle:
            csv.writer(handle, lineterminator="\n").writerows(rows)
    print(f"effects schema registration: {added} rows added")


if __name__ == "__main__":
    main()
