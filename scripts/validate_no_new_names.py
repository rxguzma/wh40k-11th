#!/usr/bin/env python3
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEW_ID_RE = re.compile(r"(?:^NEW(?:_|$)|_NEW(?:_|$)|\(New\))", re.IGNORECASE)
NEW_NAME_RE = re.compile(r"\(\s*New\s*\)", re.IGNORECASE)


def fail(message):
    raise SystemExit(message)


def main():
    issues = []
    for path in sorted((ROOT / "data").rglob("*.csv")):
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for line_no, row in enumerate(reader, start=2):
                for column, value in row.items():
                    text = (value or "").strip()
                    if not text:
                        continue
                    is_id = column == "Item_ID" or column.endswith("_ID") or column in {"Ability_ID", "Weapon_ID", "Unit_ID"}
                    is_name = column.endswith("Name") or column.endswith("_Name") or column in {"Ability Name", "Weapon Name", "Unit Name"}
                    if is_id and NEW_ID_RE.search(text):
                        issues.append(f"{path.relative_to(ROOT)}:{line_no}:{column}={text}")
                    if is_name and NEW_NAME_RE.search(text):
                        issues.append(f"{path.relative_to(ROOT)}:{line_no}:{column}={text}")
    if issues:
        fail("New naming remains in repository data:\n" + "\n".join(issues))
    print("New-name audit: OK — no '(New)' / NEW_* identifiers")


if __name__ == "__main__":
    main()
