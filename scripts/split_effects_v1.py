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
STAT_NAMES = {"M", "T", "SV", "W", "LD", "OC"}


def fail(message):
    raise SystemExit(message)


def read_dicts(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [row for row in csv.DictReader(handle) if any((value or "").strip() for value in row.values())]


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(EFFECTS_HEADER)
        writer.writerows(rows)


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
        value = set_match.group(2).strip()
        if not value:
            fail(f"{army} {source_type} {source_id}: blank SET value in tag {tag!r}")
        return ("STAT", "UNIT", set_match.group(1).upper(), "SET", value)

    keyword_match = re.fullmatch(r"([+-])\s*KEYWORD\s*:?\s*(.+)", tag, flags=re.IGNORECASE)
    if keyword_match:
        value = keyword_match.group(2).strip()
        if not value:
            fail(f"{army} {source_type} {source_id}: blank KEYWORD value in tag {tag!r}")
        operation = "ADD" if keyword_match.group(1) == "+" else "REMOVE"
        return ("KEYWORD", "UNIT", "KEYWORD", operation, value)

    fail(f"{army} {source_type} {source_id}: unknown executable tag syntax {tag!r}")


def source_rows(directory):
    for row in read_dicts(directory / "Abilities.csv"):
        yield "ABILITY", (row.get("Ability_ID") or "").strip(), row.get("Tags") or ""
    for row in read_dicts(directory / "Enhancements.csv"):
        yield "ENHANCEMENT", (row.get("Enhancement_ID") or "").strip(), row.get("Tags") or ""


def migrate_army(army):
    directory = ROOT / "data" / army
    output = []
    sources = 0
    for source_type, source_id, raw_tags in source_rows(directory):
        tags = split_tags(raw_tags)
        if not tags:
            continue
        if not source_id:
            fail(f"{army}: {source_type} row with executable Tags has no source ID")
        sources += 1
        for order, tag in enumerate(tags, start=1):
            effect_type, target, stat, operation, value = parse_tag(tag, army, source_type, source_id)
            output.append([
                f"{source_type}:{source_id}:{order}", source_type, source_id,
                effect_type, target, stat, operation, value, tag, str(order),
            ])
    write_csv(directory / "Effects.csv", output)
    print(f"{army}: {sources} tagged sources -> {len(output)} normalized effects")


def main():
    for army in ARMIES:
        migrate_army(army)
    print("effects split migration: OK")


if __name__ == "__main__":
    main()
