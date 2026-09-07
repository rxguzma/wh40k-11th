#!/usr/bin/env python3
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMIES = ("marines", "orks", "nids")
EFFECTS_HEADER = [
    "Effect_ID", "Source_Type", "Source_ID", "Effect_Type", "Target",
    "Stat", "Operation", "Value", "Display_Tag", "Sort_Order",
]
SOURCE_FILES = {
    "ABILITY": ("Abilities.csv", "Ability_ID"),
    "ENHANCEMENT": ("Enhancements.csv", "Enhancement_ID"),
}


def fail(message):
    raise SystemExit(message)


def read_table(path, expected_header=None):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if expected_header is not None and reader.fieldnames != expected_header:
            fail(
                f"{path.relative_to(ROOT)} header mismatch\n"
                f"expected: {expected_header!r}\n"
                f"actual:   {reader.fieldnames!r}"
            )
        return list(reader), list(reader.fieldnames or [])


def write_table(path, header, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_effect_tags(directory, army):
    effects, _ = read_table(directory / "Effects.csv", EFFECTS_HEADER)
    tags_by_source = defaultdict(list)
    sort_orders = defaultdict(set)

    for line_no, row in enumerate(effects, start=2):
        if not any((value or "").strip() for value in row.values()):
            continue
        source_type = (row.get("Source_Type") or "").strip().upper()
        source_id = (row.get("Source_ID") or "").strip()
        display_tag = (row.get("Display_Tag") or "").strip()
        sort_text = (row.get("Sort_Order") or "").strip()
        if source_type not in SOURCE_FILES:
            fail(f"{army}: Effects line {line_no} has invalid Source_Type {source_type!r}")
        if not source_id or not display_tag:
            fail(f"{army}: Effects line {line_no} is missing Source_ID or Display_Tag")
        try:
            sort_order = int(sort_text)
        except ValueError:
            fail(f"{army}: Effects line {line_no} has invalid Sort_Order {sort_text!r}")
        if sort_order < 1:
            fail(f"{army}: Effects line {line_no} Sort_Order must be positive")
        key = (source_type, source_id)
        if sort_order in sort_orders[key]:
            fail(f"{army}: duplicate Effects Sort_Order {sort_order} for {source_type} {source_id}")
        sort_orders[key].add(sort_order)
        tags_by_source[key].append((sort_order, display_tag))

    for key in tags_by_source:
        tags_by_source[key].sort(key=lambda item: item[0])
    return effects, tags_by_source


def sync_source_tags(directory, army, source_type, tags_by_source):
    file_name, id_column = SOURCE_FILES[source_type]
    path = directory / file_name
    rows, header = read_table(path)
    if id_column not in header or "Tags" not in header:
        fail(f"{army}: {file_name} must contain {id_column} and Tags")

    source_ids = {(row.get(id_column) or "").strip() for row in rows}
    referenced_ids = {source_id for effect_type, source_id in tags_by_source if effect_type == source_type}
    missing = sorted(source_id for source_id in referenced_ids if source_id not in source_ids)
    if missing:
        fail(f"{army}: Effects references missing {source_type} source IDs: {missing!r}")

    changed = False
    tagged_sources = 0
    for row in rows:
        source_id = (row.get(id_column) or "").strip()
        desired = ", ".join(tag for _, tag in tags_by_source.get((source_type, source_id), []))
        if desired:
            tagged_sources += 1
        current = (row.get("Tags") or "").strip()
        if current != desired:
            row["Tags"] = desired
            changed = True

    if changed:
        write_table(path, header, rows)
    return tagged_sources, changed


def sync_army(army):
    directory = ROOT / "data" / army
    effects, tags_by_source = load_effect_tags(directory, army)
    total_tagged = 0
    changed_files = []
    for source_type in ("ABILITY", "ENHANCEMENT"):
        tagged, changed = sync_source_tags(directory, army, source_type, tags_by_source)
        total_tagged += tagged
        if changed:
            changed_files.append(SOURCE_FILES[source_type][0])
    changed_text = ", ".join(changed_files) if changed_files else "current"
    print(
        f"{army}: {len([row for row in effects if any((value or '').strip() for value in row.values())])} "
        f"authoritative effects -> {total_tagged} tagged sources ({changed_text})"
    )


def main():
    for army in ARMIES:
        sync_army(army)
    print("normalized Effects -> legacy Tags compatibility sync: OK")


if __name__ == "__main__":
    main()
