#!/usr/bin/env python3
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "data" / "CSV_SCHEMA.csv"
with path.open(encoding="utf-8-sig", newline="") as handle:
    reader = csv.DictReader(handle)
    header = list(reader.fieldnames or [])
    rows = list(reader)

for row in rows:
    if row.get("Scope") == "army" and row.get("File") == "Unit_Loadout_Legacy_Units.csv":
        row["Notes"] = "Empty generated compatibility stub retained for the current HTML filename contract; no legacy unit mappings are stored."
    if row.get("Scope") == "army" and row.get("File") == "Unit_Weapon_Options.csv" and row.get("Column_Name") == "Legacy_Unit_IDs":
        row["Notes"] = "Generated blank compatibility column retained for the current HTML shape; no legacy unit mappings are stored."

with path.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
print("updated empty legacy compatibility stub metadata")
