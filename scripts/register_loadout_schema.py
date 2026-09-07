#!/usr/bin/env python3
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "data" / "CSV_SCHEMA.csv"
HEADER = ["Scope", "File", "Column_Order", "Column_Name", "Required", "Notes"]

NEW_ROWS = [
    ["army", "Unit_Loadout_Options.csv", "1", "Unit_ID", "YES", "Foreign key to Units.csv."],
    ["army", "Unit_Loadout_Options.csv", "2", "Option_Group_ID", "YES", "Stable option-group key within a unit."],
    ["army", "Unit_Loadout_Options.csv", "3", "Group_Label", "NO", "Visible option-group label."],
    ["army", "Unit_Loadout_Options.csv", "4", "Option_ID", "YES", "Stable loadout option key."],
    ["army", "Unit_Loadout_Options.csv", "5", "Option_Name", "YES", "Visible loadout option name."],
    ["army", "Unit_Loadout_Options.csv", "6", "Default", "YES", "Exactly one default option per unit/group."],
    ["army", "Unit_Loadout_Options.csv", "7", "Sort_Order", "YES", "Display order within the option group."],
    ["army", "Unit_Loadout_Weapons.csv", "1", "Unit_ID", "YES", "Foreign key to Units.csv."],
    ["army", "Unit_Loadout_Weapons.csv", "2", "Option_Group_ID", "YES", "Foreign key component to Unit_Loadout_Options.csv."],
    ["army", "Unit_Loadout_Weapons.csv", "3", "Option_ID", "YES", "Foreign key component to Unit_Loadout_Options.csv."],
    ["army", "Unit_Loadout_Weapons.csv", "4", "Weapon_ID", "YES", "Foreign key to Weapon_Stats.csv."],
    ["army", "Unit_Loadout_Weapons.csv", "5", "Weapon_Role", "YES", "SELECTED adds/replaces the option weapons; PRESERVE retains a base weapon."],
    ["army", "Unit_Loadout_Weapons.csv", "6", "Sort_Order", "YES", "Order within the selected or preserved weapon list."],
    ["army", "Unit_Loadout_Abilities.csv", "1", "Unit_ID", "YES", "Foreign key to Units.csv."],
    ["army", "Unit_Loadout_Abilities.csv", "2", "Option_Group_ID", "YES", "Foreign key component to Unit_Loadout_Options.csv."],
    ["army", "Unit_Loadout_Abilities.csv", "3", "Option_ID", "YES", "Foreign key component to Unit_Loadout_Options.csv."],
    ["army", "Unit_Loadout_Abilities.csv", "4", "Ability_ID", "YES", "Ability granted by selecting this loadout option."],
    ["army", "Unit_Loadout_Abilities.csv", "5", "Sort_Order", "YES", "Order within the option ability list."],
    ["army", "Unit_Loadout_Points.csv", "1", "Unit_ID", "YES", "Foreign key to Units.csv."],
    ["army", "Unit_Loadout_Points.csv", "2", "Option_Group_ID", "YES", "Foreign key component to Unit_Loadout_Options.csv."],
    ["army", "Unit_Loadout_Points.csv", "3", "Option_ID", "YES", "Foreign key component to Unit_Loadout_Options.csv."],
    ["army", "Unit_Loadout_Points.csv", "4", "Point_Option_ID", "YES", "Stable option-specific point slot key."],
    ["army", "Unit_Loadout_Points.csv", "5", "Label", "NO", "Option-specific unit-size label; blank is valid."],
    ["army", "Unit_Loadout_Points.csv", "6", "Cost", "NO", "Option-specific point cost; blank is valid for loadout-driven behavior."],
    ["army", "Unit_Loadout_Points.csv", "7", "Sort_Order", "YES", "Point-option display order."],
    ["army", "Unit_Loadout_Compatibility.csv", "1", "Unit_ID", "YES", "Foreign key to Units.csv."],
    ["army", "Unit_Loadout_Compatibility.csv", "2", "Option_Group_ID", "YES", "Source option group."],
    ["army", "Unit_Loadout_Compatibility.csv", "3", "Option_ID", "YES", "Source option."],
    ["army", "Unit_Loadout_Compatibility.csv", "4", "Required_Group_ID", "YES", "Other option group constrained by this rule."],
    ["army", "Unit_Loadout_Compatibility.csv", "5", "Compatible_Option_ID", "YES", "Allowed option in Required_Group_ID; multiple rows are OR alternatives."],
    ["army", "Unit_Loadout_Compatibility.csv", "6", "Rule_Order", "YES", "Original compatibility rule order."],
    ["army", "Unit_Loadout_Compatibility.csv", "7", "Option_Order", "YES", "Original allowed-option order within the rule."],
    ["army", "Unit_Loadout_Legacy_Units.csv", "1", "Unit_ID", "YES", "Canonical unit receiving the loadout option."],
    ["army", "Unit_Loadout_Legacy_Units.csv", "2", "Option_Group_ID", "YES", "Foreign key component to Unit_Loadout_Options.csv."],
    ["army", "Unit_Loadout_Legacy_Units.csv", "3", "Option_ID", "YES", "Foreign key component to Unit_Loadout_Options.csv."],
    ["army", "Unit_Loadout_Legacy_Units.csv", "4", "Legacy_Unit_ID", "YES", "Historical unit ID migrated to this selected option."],
    ["army", "Unit_Loadout_Legacy_Units.csv", "5", "Sort_Order", "YES", "Original alias order."],
]


def main():
    with PATH.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    if not rows or rows[0] != HEADER:
        raise SystemExit(f"unexpected CSV_SCHEMA.csv header: {rows[0] if rows else None!r}")
    existing = {(row[0], row[1], row[3]) for row in rows[1:] if len(row) >= 4}
    added = 0
    for row in NEW_ROWS:
        key = (row[0], row[1], row[3])
        if key not in existing:
            rows.append(row)
            existing.add(key)
            added += 1
    if added:
        with PATH.open("w", encoding="utf-8", newline="") as handle:
            csv.writer(handle, lineterminator="\n").writerows(rows)
    print(f"loadout schema registration: {added} rows added")


if __name__ == "__main__":
    main()
