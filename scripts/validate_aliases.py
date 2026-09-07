#!/usr/bin/env python3
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMIES = ("marines", "orks", "nids")
HEADER = ["Entity_Type", "Army", "Alias_ID", "Canonical_ID", "Status"]
NEW_ID_RE = re.compile(r"(?:^NEW(?:_|$)|_NEW(?:_|$)|\(New\))", re.IGNORECASE)
TARGETS = {
    "unit": ("army", "Unit_Profiles.csv", "Unit_ID"),
    "weapon": ("army", "Weapon_Stats.csv", "Weapon_ID"),
    "ability": ("army", "Abilities.csv", "Ability_ID"),
    "detachment": ("army", "Detachment_Definitions.csv", "Detachment_ID"),
    "enhancement": ("army", "Enhancements.csv", "Enhancement_ID"),
    "stratagem": ("army", "Stratagems.csv", "Stratagem_ID"),
    "army_rule": ("army", "Army_Rules.csv", "Army_Rule_ID"),
    "effect": ("army", "Effects.csv", "Effect_ID"),
    "loadout_option": ("army", "Loadout_Options.csv", "Loadout_Option_ID"),
    "universal_ability": ("universal", "Universal_Abilities.csv", "Ability_ID"),
    "universal_stratagem": ("universal", "Universal_Stratagems.csv", "Item_ID"),
}


def fail(message):
    raise SystemExit(message)


def ids(path, column):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return {(row.get(column) or "").strip() for row in reader if (row.get(column) or "").strip()}


def main():
    path = ROOT / "data" / "universal" / "Entity_Aliases.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != HEADER:
            fail(f"Entity_Aliases.csv header mismatch: {reader.fieldnames!r}")
        rows = list(reader)
    seen = {}
    alias_keys = set()
    for line_no, row in enumerate(rows, start=2):
        entity = (row.get("Entity_Type") or "").strip()
        army = (row.get("Army") or "").strip()
        alias_id = (row.get("Alias_ID") or "").strip()
        canonical_id = (row.get("Canonical_ID") or "").strip()
        status = (row.get("Status") or "").strip()
        if entity not in TARGETS:
            fail(f"line {line_no}: unsupported Entity_Type {entity!r}")
        scope, filename, id_col = TARGETS[entity]
        if scope == "universal" and army != "universal":
            fail(f"line {line_no}: {entity} requires Army=universal")
        if scope == "army" and army not in ARMIES:
            fail(f"line {line_no}: {entity} requires an army slug")
        if not alias_id or not canonical_id or alias_id == canonical_id:
            fail(f"line {line_no}: invalid alias identity")
        if status != "DEPRECATED":
            fail(f"line {line_no}: Status must be DEPRECATED")
        if NEW_ID_RE.search(canonical_id):
            fail(f"line {line_no}: canonical ID still contains New marker: {canonical_id!r}")
        key = (entity, army, alias_id)
        if key in seen:
            fail(f"duplicate alias {key!r}: lines {seen[key]} and {line_no}")
        seen[key] = line_no
        alias_keys.add(key)
        target_path = ROOT / "data" / ("universal" if scope == "universal" else army) / filename
        if canonical_id not in ids(target_path, id_col):
            fail(f"line {line_no}: missing canonical target {canonical_id!r} in {target_path.relative_to(ROOT)}")
    for row in rows:
        key = (row["Entity_Type"], row["Army"], row["Canonical_ID"])
        if key in alias_keys:
            fail(f"alias chain is not allowed: {row['Alias_ID']!r} -> {row['Canonical_ID']!r}")
    print(f"entity aliases OK — {len(rows)} deprecated aliases")


if __name__ == "__main__":
    main()
