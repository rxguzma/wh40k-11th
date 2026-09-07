#!/usr/bin/env python3
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMIES = ("marines", "orks", "nids")

EXPECTED = [
    "Detachment_ID",
    "Army_Name",
    "Detachment_Name",
    "Item_Type",
    "Item_ID",
    "Item_Name",
    "Points",
    "CP_Cost",
    "DP_Cost",
    "Detachment_Disposition",
    "Short_Description",
    "Long_Description",
    "Detachment_Disposition_2",
]

DEFINITION_HEADER = [
    "Detachment_ID",
    "Army_Name",
    "Detachment_Name",
    "Rule_ID",
    "Rule_Name",
    "DP_Cost",
    "Detachment_Disposition",
    "Detachment_Disposition_2",
    "Short_Description",
    "Long_Description",
]

ENHANCEMENT_HEADER = [
    "Enhancement_ID",
    "Detachment_ID",
    "Enhancement_Name",
    "Points",
    "Short_Description",
    "Long_Description",
    "Tags",
]

STRATAGEM_HEADER = [
    "Stratagem_ID",
    "Detachment_ID",
    "Stratagem_Name",
    "CP_Cost",
    "Short_Description",
    "Long_Description",
]

ARMY_RULE_HEADER = [
    "Army_Rule_ID",
    "Army_Name",
    "Rule_Name",
    "Short_Description",
    "Long_Description",
]


def fail(message):
    raise SystemExit(message)


def read_source(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != EXPECTED:
            fail(f"{path.relative_to(ROOT)} header mismatch: {reader.fieldnames!r}")
        return list(reader)


def require_unique(rows, key, label, army):
    seen = set()
    for row in rows:
        value = (row.get(key) or "").strip()
        if not value:
            fail(f"{army}: blank {label}")
        if value in seen:
            fail(f"{army}: duplicate {label} {value!r}")
        seen.add(value)


def write_csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def migrate_army(army):
    source = ROOT / "data" / army / "Detachments.csv"
    rows = read_source(source)

    definitions = []
    enhancements = []
    stratagems = []
    army_rules = []

    definition_source = []
    enhancement_source = []
    stratagem_source = []
    army_rule_source = []

    for row in rows:
        item_type = (row.get("Item_Type") or "").strip().upper()
        if item_type == "DETACHMENT_RULE":
            definition_source.append(row)
            definitions.append([
                row["Detachment_ID"],
                row["Army_Name"],
                row["Detachment_Name"],
                row["Item_ID"],
                row["Item_Name"],
                row["DP_Cost"],
                row["Detachment_Disposition"],
                row["Detachment_Disposition_2"],
                row["Short_Description"],
                row["Long_Description"],
            ])
        elif item_type == "ENHANCEMENT":
            enhancement_source.append(row)
            enhancements.append([
                row["Item_ID"],
                row["Detachment_ID"],
                row["Item_Name"],
                row["Points"],
                row["Short_Description"],
                row["Long_Description"],
                "",
            ])
        elif item_type == "STRATAGEM":
            stratagem_source.append(row)
            stratagems.append([
                row["Item_ID"],
                row["Detachment_ID"],
                row["Item_Name"],
                row["CP_Cost"],
                row["Short_Description"],
                row["Long_Description"],
            ])
        elif item_type == "ARMY_RULE":
            army_rule_source.append(row)
            army_rules.append([
                row["Item_ID"],
                row["Army_Name"],
                row["Item_Name"],
                row["Short_Description"],
                row["Long_Description"],
            ])
        else:
            fail(f"{army}: unsupported Item_Type {item_type!r}")

    require_unique(definition_source, "Detachment_ID", "Detachment_ID", army)
    require_unique(definition_source, "Item_ID", "detachment Rule_ID", army)
    require_unique(enhancement_source, "Item_ID", "Enhancement_ID", army)
    require_unique(stratagem_source, "Item_ID", "Stratagem_ID", army)
    require_unique(army_rule_source, "Item_ID", "Army_Rule_ID", army)

    detachment_ids = {(row.get("Detachment_ID") or "").strip() for row in definition_source}
    for row in enhancement_source + stratagem_source:
        parent = (row.get("Detachment_ID") or "").strip()
        if parent not in detachment_ids:
            fail(f"{army}: child {row.get('Item_ID')!r} references missing detachment {parent!r}")

    directory = ROOT / "data" / army
    write_csv(directory / "Detachment_Definitions.csv", DEFINITION_HEADER, definitions)
    write_csv(directory / "Enhancements.csv", ENHANCEMENT_HEADER, enhancements)
    write_csv(directory / "Stratagems.csv", STRATAGEM_HEADER, stratagems)
    write_csv(directory / "Army_Rules.csv", ARMY_RULE_HEADER, army_rules)

    source_count = len(rows)
    split_count = len(definitions) + len(enhancements) + len(stratagems) + len(army_rules)
    if source_count != split_count:
        fail(f"{army}: row-count mismatch source={source_count} split={split_count}")

    print(
        f"{army}: {source_count} rows -> "
        f"{len(definitions)} detachments, {len(enhancements)} enhancements, "
        f"{len(stratagems)} stratagems, {len(army_rules)} army rules"
    )


def main():
    for army in ARMIES:
        migrate_army(army)
    print("detachment split migration: OK")


if __name__ == "__main__":
    main()
