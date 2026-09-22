#!/usr/bin/env python3
# Canonical Ability Visibility_ID is required data; application code must not infer placement.
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
        if "Ability_ID" not in header or "Visibility_ID" not in header:
            fail(f"{path.relative_to(ROOT)} must contain Ability_ID and Visibility_ID")
        rows = list(reader)
    seen = set()
    for line_no, row in enumerate(rows, start=2):
        ability_id = (row.get("Ability_ID") or "").strip()
        visibility = (row.get("Visibility_ID") or "").strip()
        if not ability_id:
            fail(f"{path.relative_to(ROOT)} line {line_no}: blank Ability_ID")
        if ability_id in seen:
            fail(f"{path.relative_to(ROOT)} line {line_no}: duplicate Ability_ID {ability_id!r}")
        seen.add(ability_id)
        if not re.fullmatch(r"[1-3]", visibility):
            fail(f"{path.relative_to(ROOT)} line {line_no}: Ability {ability_id!r} requires Visibility_ID 1-3, found {visibility!r}")
    print(f"{path.relative_to(ROOT)}: {len(rows)} Ability Visibility_ID values valid")
