#!/usr/bin/env python3
import csv
import re
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
VALID_STATS = {"M", "T", "SV", "W", "LD", "OC"}


def fail(message):
    raise SystemExit(message)


def read_dicts(path, expected_header=None):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if expected_header is not None and reader.fieldnames != expected_header:
            fail(f"{path.relative_to(ROOT)} header mismatch: {reader.fieldnames!r}")
        return [row for row in reader if any((value or "").strip() for value in row.values())]


def parse_display_tag(tag, army, effect_id):
    point_match = re.fullmatch(r"([+-]\d+)\s*PTS", tag, flags=re.IGNORECASE)
    if point_match:
        return ("POINTS_PER_MODEL", "UNIT", "PTS", "ADD", str(int(point_match.group(1))))

    add_match = re.fullmatch(r"([+-]\d+)\s*(M|T|SV|W|LD|OC)", tag, flags=re.IGNORECASE)
    if add_match:
        return ("STAT", "UNIT", add_match.group(2).upper(), "ADD", str(int(add_match.group(1))))

    set_match = re.fullmatch(r"(M|T|SV|W|LD|OC)\s*=\s*(.+)", tag, flags=re.IGNORECASE)
    if set_match:
        value = set_match.group(2).strip()
        if value:
            return ("STAT", "UNIT", set_match.group(1).upper(), "SET", value)

    keyword_match = re.fullmatch(r"([+-])\s*KEYWORD\s*:?\s*(.+)", tag, flags=re.IGNORECASE)
    if keyword_match:
        value = keyword_match.group(2).strip()
        if value:
            return (
                "KEYWORD", "UNIT", "KEYWORD",
                "ADD" if keyword_match.group(1) == "+" else "REMOVE",
                value,
            )

    fail(f"{army}: effect {effect_id} has Display_Tag that does not match supported modifier syntax: {tag!r}")


def validate_army(army):
    directory = ROOT / "data" / army
    source_rows = {}
    source_ids = {}
    for source_type, (file_name, id_column) in SOURCE_FILES.items():
        rows = read_dicts(directory / file_name)
        source_rows[source_type] = rows
        source_ids[source_type] = {(row.get(id_column) or "").strip() for row in rows}

    effects = read_dicts(directory / "Effects.csv", EFFECTS_HEADER)
    tags_by_source = defaultdict(list)
    seen_effect_ids = set()
    seen_sort_orders = defaultdict(set)

    for line_no, row in enumerate(effects, start=2):
        effect_id = (row.get("Effect_ID") or "").strip()
        source_type = (row.get("Source_Type") or "").strip().upper()
        source_id = (row.get("Source_ID") or "").strip()
        effect_type = (row.get("Effect_Type") or "").strip().upper()
        target = (row.get("Target") or "").strip().upper()
        stat = (row.get("Stat") or "").strip().upper()
        operation = (row.get("Operation") or "").strip().upper()
        value = (row.get("Value") or "").strip()
        display_tag = (row.get("Display_Tag") or "").strip()
        sort_text = (row.get("Sort_Order") or "").strip()

        if not effect_id or effect_id in seen_effect_ids:
            fail(f"{army}: blank or duplicate Effect_ID {effect_id!r} at line {line_no}")
        seen_effect_ids.add(effect_id)
        if source_type not in SOURCE_FILES:
            fail(f"{army}: effect {effect_id} has invalid Source_Type {source_type!r}")
        if source_id not in source_ids[source_type]:
            fail(f"{army}: effect {effect_id} references missing {source_type} source {source_id!r}")
        if target != "UNIT":
            fail(f"{army}: effect {effect_id} has invalid Target {target!r}")
        if not value or not display_tag:
            fail(f"{army}: effect {effect_id} is missing Value or Display_Tag")
        try:
            sort_order = int(sort_text)
        except ValueError:
            fail(f"{army}: effect {effect_id} has invalid Sort_Order {sort_text!r}")
        if sort_order < 1:
            fail(f"{army}: effect {effect_id} Sort_Order must be positive")
        source_key = (source_type, source_id)
        if sort_order in seen_sort_orders[source_key]:
            fail(f"{army}: duplicate Sort_Order {sort_order} for {source_type} {source_id}")
        seen_sort_orders[source_key].add(sort_order)
        expected_effect_id = f"{source_type}:{source_id}:{sort_order}"
        if effect_id != expected_effect_id:
            fail(f"{army}: Effect_ID {effect_id!r} must equal {expected_effect_id!r}")

        if effect_type == "STAT":
            if stat not in VALID_STATS or operation not in {"ADD", "SET"}:
                fail(f"{army}: invalid STAT effect {effect_id}")
            if operation == "ADD":
                try:
                    canonical_value = str(int(value))
                except ValueError:
                    fail(f"{army}: STAT ADD effect {effect_id} requires an integer Value")
                if value != canonical_value:
                    fail(f"{army}: STAT ADD effect {effect_id} requires canonical integer Value {canonical_value!r}")
        elif effect_type == "POINTS_PER_MODEL":
            if stat != "PTS" or operation != "ADD":
                fail(f"{army}: invalid POINTS_PER_MODEL effect {effect_id}")
            try:
                canonical_value = str(int(value))
            except ValueError:
                fail(f"{army}: POINTS_PER_MODEL effect {effect_id} requires an integer Value")
            if value != canonical_value:
                fail(f"{army}: POINTS_PER_MODEL effect {effect_id} requires canonical integer Value {canonical_value!r}")
        elif effect_type == "KEYWORD":
            if stat != "KEYWORD" or operation not in {"ADD", "REMOVE"}:
                fail(f"{army}: invalid KEYWORD effect {effect_id}")
        else:
            fail(f"{army}: effect {effect_id} has invalid Effect_Type {effect_type!r}")

        parsed_display = parse_display_tag(display_tag, army, effect_id)
        expected_tuple = (effect_type, target, stat, operation, value)
        compare_parsed = parsed_display
        if effect_type == "KEYWORD":
            compare_parsed = (*parsed_display[:4], parsed_display[4].upper())
            expected_tuple = (*expected_tuple[:4], expected_tuple[4].upper())
        if compare_parsed != expected_tuple:
            fail(
                f"{army}: effect {effect_id} Display_Tag {display_tag!r} does not describe "
                f"its structured mechanics {expected_tuple!r}"
            )

        tags_by_source[source_key].append((sort_order, display_tag))

    for key in tags_by_source:
        tags_by_source[key].sort(key=lambda item: item[0])

    for source_type, (file_name, id_column) in SOURCE_FILES.items():
        for row in source_rows[source_type]:
            source_id = (row.get(id_column) or "").strip()
            expected_tags = ", ".join(tag for _, tag in tags_by_source.get((source_type, source_id), []))
            actual_tags = (row.get("Tags") or "").strip()
            if actual_tags != expected_tags:
                fail(
                    f"{army}: {file_name} {source_id} Tags {actual_tags!r} do not match "
                    f"authoritative Effects display tags {expected_tags!r}"
                )

    print(f"{army}: effects OK — {len(effects)} authoritative effects")


def main():
    for army in ARMIES:
        validate_army(army)
    print("authoritative effects validation: OK")


if __name__ == "__main__":
    main()
