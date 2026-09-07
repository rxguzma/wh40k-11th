#!/usr/bin/env python3
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ROWS = {
    "data/marines/Weapon_Stats.csv": [
        ["HEAVY_BOLT_PISTOL_AETHON", "Heavy bolt pistol", '18"', "1", "2", "4", "-1", "1", "PISTOL"],
        ["BOLT_PISTOL_X4_CH", "Bolt pistol x4", '12"', "4", "3", "4", "0", "1", "PISTOL"],
        ["BOLT_RIFLE_X1_CH", "Bolt rifle", '24"', "2", "3", "4", "-1", "1", ""],
        ["MASTER_CRAFTED_BOLT_RIFLE_X1_CH", "Master-crafted bolt rifle", '24"', "2", "2", "4", "-1", "2", "DEVASTATING WOUNDS, RAPID FIRE 1"],
        ["MASTER_CRAFTED_HEAVY_BOLTER_X1_CH", "Master-crafted heavy bolter", '36"', "3", "3", "5", "-1", "3", "HEAVY, SUSTAINED HITS 2"],
        ["CLOSE_COMBAT_WEAPON_X3_CH", "Close combat weapon x3", "-", "15", "3", "4", "0", "1", ""],
        ["MASTER_CRAFTED_POWER_WEAPON_X1_CH", "Master-crafted power weapon", "-", "6", "2", "5", "-2", "2", "PRECISION"],
    ],
    "data/orks/Weapon_Stats.csv": [
        ["BIG_SHOOTA_BATTLEWAGON", "Big shoota", '36"', "3", "5", "5", "0", "1", "RAPID FIRE 2"],
    ],
    "data/universal/Universal_Abilities.csv": [
        [
            "FIRING_DECK_2",
            "Firing Deck 2",
            "Firing Deck 2",
            "Firing Deck: This ability always takes the form Firing Deck X. In your Shooting phase, each time this TRANSPORT is selected to shoot, if one or more units are embarked within it, select up to X embarked models, excluding models whose units have already been selected to shoot this phase. For each selected model, select one of its ranged weapons, excluding [ONE SHOT] weapons. Until this TRANSPORT has resolved all of its attacks, it has all selected weapons in addition to its other weapons. Until the end of the turn, units embarked within this TRANSPORT are not eligible to shoot.",
        ],
    ],
}


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.reader(handle))


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle, lineterminator="\n").writerows(rows)


def dedupe_identical_rows():
    changed = False
    for path in sorted((ROOT / "data").glob("**/*.csv")):
        rows = read_csv(path)
        if not rows:
            continue
        seen = set()
        kept = [rows[0]]
        removed = 0
        for row in rows[1:]:
            key = tuple(row)
            if key in seen:
                removed += 1
                continue
            seen.add(key)
            kept.append(row)
        if removed:
            write_csv(path, kept)
            changed = True
            print(f"removed {removed} identical duplicate row(s) from {path.relative_to(ROOT)}")
    return changed


def add_missing_rows(rel_path, additions):
    path = ROOT / rel_path
    rows = read_csv(path)
    if not rows:
        raise SystemExit(f"empty CSV: {rel_path}")
    header = rows[0]
    existing = {row[0] for row in rows[1:] if row}
    changed = False
    for row in additions:
        if row[0] in existing:
            continue
        if len(row) != len(header):
            raise SystemExit(f"migration row width mismatch for {rel_path} {row[0]}")
        rows.append(row)
        existing.add(row[0])
        changed = True
        print(f"inserted {rel_path} {row[0]}")
    if changed:
        write_csv(path, rows)
    return changed


def main():
    changed = dedupe_identical_rows()
    for rel_path, additions in ROWS.items():
        changed = add_missing_rows(rel_path, additions) or changed
    print("schema v1 reference migration:", "changed" if changed else "already applied")


if __name__ == "__main__":
    main()
