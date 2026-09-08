#!/usr/bin/env python3
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    ROOT / "data" / "marines" / "Abilities.csv",
    ROOT / "data" / "orks" / "Abilities.csv",
    ROOT / "data" / "nids" / "Abilities.csv",
    ROOT / "data" / "universal" / "Universal_Abilities.csv",
]

def fail(message):
    raise SystemExit(message)

for path in FILES:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        header = list(reader.fieldnames or [])
        if "Ability_ID" not in header or "Order" not in header:
            fail(f"{path.relative_to(ROOT)} must contain Ability_ID and Order")
        rows = list(reader)
    seen = set()
    for line_no, row in enumerate(rows, start=2):
        ability_id = (row.get("Ability_ID") or "").strip()
        order = (row.get("Order") or "").strip()
        if not ability_id:
            fail(f"{path.relative_to(ROOT)} line {line_no}: blank Ability_ID")
        if ability_id in seen:
            fail(f"{path.relative_to(ROOT)} line {line_no}: duplicate Ability_ID {ability_id!r}")
        seen.add(ability_id)
        if not re.fullmatch(r"[0-9]", order):
            fail(f"{path.relative_to(ROOT)} line {line_no}: Ability {ability_id!r} requires Order 0-9, found {order!r}")
    print(f"{path.relative_to(ROOT)}: {len(rows)} Ability Orders valid")
