#!/usr/bin/env python3
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMIES = ("marines", "orks", "nids")

LEGACY_HEADER = [
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
    "Repeatable",
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


def read_csv(path, expected_header):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != expected_header:
            fail(f"{path.relative_to(ROOT)} header mismatch: {reader.fieldnames!r}")
        rows = list(reader)
    return [row for row in rows if any((value or "").strip() for value in row.values())]


def require_unique(rows, key, label, army):
    seen = set()
    for row in rows:
        value = (row.get(key) or "").strip()
        if not value:
            fail(f"{army}: blank {label}")
        if value in seen:
            fail(f"{army}: duplicate {label} {value!r}")
        seen.add(value)


def slugify(value):
    text = str(value or "").strip().lower().replace("’", "").replace("'", "")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_") or "army_rule"


def csv_text(header, rows):
    from io import StringIO

    buffer = StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue()


def write_if_changed(path, header, rows):
    content = csv_text(header, rows)
    old = path.read_text(encoding="utf-8-sig") if path.exists() else None
    if old == content:
        return False
    path.write_text(content, encoding="utf-8", newline="")
    return True


def sync_army(army):
    directory = ROOT / "data" / army
    definitions = read_csv(directory / "Detachment_Definitions.csv", DEFINITION_HEADER)
    enhancements = read_csv(directory / "Enhancements.csv", ENHANCEMENT_HEADER)
    stratagems = read_csv(directory / "Stratagems.csv", STRATAGEM_HEADER)
    army_rules = read_csv(directory / "Army_Rules.csv", ARMY_RULE_HEADER)

    require_unique(definitions, "Detachment_ID", "Detachment_ID", army)
    require_unique(definitions, "Rule_ID", "Rule_ID", army)
    require_unique(enhancements, "Enhancement_ID", "Enhancement_ID", army)
    require_unique(stratagems, "Stratagem_ID", "Stratagem_ID", army)
    require_unique(army_rules, "Army_Rule_ID", "Army_Rule_ID", army)

    definition_by_id = {(row["Detachment_ID"] or "").strip(): row for row in definitions}
    enhancements_by_parent = {detachment_id: [] for detachment_id in definition_by_id}
    stratagems_by_parent = {detachment_id: [] for detachment_id in definition_by_id}

    for row in enhancements:
        parent = (row["Detachment_ID"] or "").strip()
        if parent not in definition_by_id:
            fail(f"{army}: enhancement {row['Enhancement_ID']!r} references missing detachment {parent!r}")
        enhancements_by_parent[parent].append(row)

    for row in stratagems:
        parent = (row["Detachment_ID"] or "").strip()
        if parent not in definition_by_id:
            fail(f"{army}: stratagem {row['Stratagem_ID']!r} references missing detachment {parent!r}")
        stratagems_by_parent[parent].append(row)

    legacy_rows = []
    for definition in definitions:
        detachment_id = definition["Detachment_ID"]
        army_name = definition["Army_Name"]
        detachment_name = definition["Detachment_Name"]
        legacy_rows.append([
            detachment_id,
            army_name,
            detachment_name,
            "DETACHMENT_RULE",
            definition["Rule_ID"],
            definition["Rule_Name"],
            "",
            "",
            definition["DP_Cost"],
            definition["Detachment_Disposition"],
            definition["Short_Description"],
            definition["Long_Description"],
            definition["Detachment_Disposition_2"],
        ])

        for enhancement in enhancements_by_parent[detachment_id]:
            legacy_rows.append([
                detachment_id,
                army_name,
                detachment_name,
                "ENHANCEMENT",
                enhancement["Enhancement_ID"],
                enhancement["Enhancement_Name"],
                enhancement["Points"],
                "",
                "",
                "",
                enhancement["Short_Description"],
                enhancement["Long_Description"],
                "",
            ])

        for stratagem in stratagems_by_parent[detachment_id]:
            legacy_rows.append([
                detachment_id,
                army_name,
                detachment_name,
                "STRATAGEM",
                stratagem["Stratagem_ID"],
                stratagem["Stratagem_Name"],
                "",
                stratagem["CP_Cost"],
                "",
                "",
                stratagem["Short_Description"],
                stratagem["Long_Description"],
                "",
            ])

    for rule in army_rules:
        legacy_rows.append([
            slugify(rule["Army_Name"]),
            rule["Army_Name"],
            "",
            "ARMY_RULE",
            rule["Army_Rule_ID"],
            rule["Rule_Name"],
            "",
            "",
            "",
            "",
            rule["Short_Description"],
            rule["Long_Description"],
            "",
        ])

    normalized_count = len(definitions) + len(enhancements) + len(stratagems) + len(army_rules)
    if len(legacy_rows) != normalized_count:
        fail(f"{army}: row-count mismatch normalized={normalized_count} legacy={len(legacy_rows)}")

    changed = write_if_changed(directory / "Detachments.csv", LEGACY_HEADER, legacy_rows)
    print(
        f"{army}: {normalized_count} normalized rows -> legacy Detachments.csv "
        f"({'updated' if changed else 'current'})"
    )


def main():
    for army in ARMIES:
        sync_army(army)
    print("normalized detachment compatibility sync: OK")


if __name__ == "__main__":
    main()
