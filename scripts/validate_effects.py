#!/usr/bin/env python3
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMIES = ("marines", "orks", "nids")
EFFECTS_HEADER = [
    "Effect_ID", "Source_Type", "Source_ID", "Effect_Type", "Target",
    "Stat", "Operation", "Value", "Display_Tag", "Sort_Order",
]


def fail(message):
    raise SystemExit(message)


def read_dicts(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if path.name == "Effects.csv" and reader.fieldnames != EFFECTS_HEADER:
            fail(f"{path.relative_to(ROOT)} header mismatch: {reader.fieldnames!r}")
        return [row for row in reader if any((value or "").strip() for value in row.values())]


def split_tags(value):
    return [
        token.strip().lstrip("[").rstrip("]").strip()
        for token in re.split(r"[,;\r\n]+", str(value or ""))
        if token.strip().lstrip("[").rstrip("]").strip()
    ]


def parse_tag(tag, army, source_type, source_id):
    point_match = re.fullmatch(r"([+-]\d+)\s*PTS", tag, flags=re.IGNORECASE)
    if point_match:
        return ("POINTS_PER_MODEL", "UNIT", "PTS", "ADD", str(int(point_match.group(1))))
    add_match = re.fullmatch(r"([+-]\d+)\s*(M|T|SV|W|LD|OC)", tag, flags=re.IGNORECASE)
    if add_match:
        return ("STAT", "UNIT", add_match.group(2).upper(), "ADD", str(int(add_match.group(1))))
    set_match = re.fullmatch(r"(M|T|SV|W|LD|OC)\s*=\s*(.+)", tag, flags=re.IGNORECASE)
    if set_match:
        return ("STAT", "UNIT", set_match.group(1).upper(), "SET", set_match.group(2).strip())
    keyword_match = re.fullmatch(r"([+-])\s*KEYWORD\s*:?\s*(.+)", tag, flags=re.IGNORECASE)
    if keyword_match:
        return (
            "KEYWORD", "UNIT", "KEYWORD",
            "ADD" if keyword_match.group(1) == "+" else "REMOVE",
            keyword_match.group(2).strip(),
        )
    fail(f"{army} {source_type} {source_id}: unknown executable tag syntax {tag!r}")


def expected_rows(directory, army):
    expected = []
    for source_type, file_name, id_column in (
        ("ABILITY", "Abilities.csv", "Ability_ID"),
        ("ENHANCEMENT", "Enhancements.csv", "Enhancement_ID"),
    ):
        for row in read_dicts(directory / file_name):
            source_id = (row.get(id_column) or "").strip()
            tags = split_tags(row.get("Tags"))
            for order, tag in enumerate(tags, start=1):
                parsed = parse_tag(tag, army, source_type, source_id)
                expected.append((
                    f"{source_type}:{source_id}:{order}", source_type, source_id,
                    *parsed, tag, str(order),
                ))
    return expected


def validate_army(army):
    directory = ROOT / "data" / army
    abilities = read_dicts(directory / "Abilities.csv")
    enhancements = read_dicts(directory / "Enhancements.csv")
    effects = read_dicts(directory / "Effects.csv")

    ability_ids = {(row.get("Ability_ID") or "").strip() for row in abilities}
    enhancement_ids = {(row.get("Enhancement_ID") or "").strip() for row in enhancements}
    expected = expected_rows(directory, army)
    actual = [tuple((row.get(column) or "").strip() for column in EFFECTS_HEADER) for row in effects]
    if actual != expected:
        fail(f"{army}: Effects.csv does not exactly match executable Tags")

    seen = set()
    for row in effects:
        effect_id = (row.get("Effect_ID") or "").strip()
        source_type = (row.get("Source_Type") or "").strip().upper()
        source_id = (row.get("Source_ID") or "").strip()
        effect_type = (row.get("Effect_Type") or "").strip().upper()
        target = (row.get("Target") or "").strip().upper()
        stat = (row.get("Stat") or "").strip().upper()
        operation = (row.get("Operation") or "").strip().upper()
        value = (row.get("Value") or "").strip()
        display_tag = (row.get("Display_Tag") or "").strip()
        sort_order = (row.get("Sort_Order") or "").strip()

        if not effect_id or effect_id in seen:
            fail(f"{army}: blank or duplicate Effect_ID {effect_id!r}")
        seen.add(effect_id)
        if source_type == "ABILITY":
            if source_id not in ability_ids:
                fail(f"{army}: effect {effect_id} references missing Ability_ID {source_id!r}")
        elif source_type == "ENHANCEMENT":
            if source_id not in enhancement_ids:
                fail(f"{army}: effect {effect_id} references missing Enhancement_ID {source_id!r}")
        else:
            fail(f"{army}: effect {effect_id} has invalid Source_Type {source_type!r}")
        if target != "UNIT":
            fail(f"{army}: effect {effect_id} has invalid Target {target!r}")
        if effect_type == "STAT":
            if stat not in {"M", "T", "SV", "W", "LD", "OC"} or operation not in {"ADD", "SET"}:
                fail(f"{army}: invalid STAT effect {effect_id}")
        elif effect_type == "POINTS_PER_MODEL":
            if stat != "PTS" or operation != "ADD" or not re.fullmatch(r"[+-]?\d+", value):
                fail(f"{army}: invalid POINTS_PER_MODEL effect {effect_id}")
        elif effect_type == "KEYWORD":
            if stat != "KEYWORD" or operation not in {"ADD", "REMOVE"}:
                fail(f"{army}: invalid KEYWORD effect {effect_id}")
        else:
            fail(f"{army}: effect {effect_id} has invalid Effect_Type {effect_type!r}")
        if not value or not display_tag or not sort_order.isdigit():
            fail(f"{army}: incomplete effect {effect_id}")

    print(f"{army}: effects OK — {len(effects)} effects")


def main():
    for army in ARMIES:
        validate_army(army)
    print("effects validation: OK")


if __name__ == "__main__":
    main()
