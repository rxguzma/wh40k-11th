#!/usr/bin/env python3
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMIES = ("marines", "orks", "nids")
PROFILE_HEADER = ["Unit_ID", "Unit Name", 'M"', "T", "SV", "W", "LD", "OC", "Keywords", "Hyperlink"]
UNITS_HEADER = ["Unit_ID", "Unit Name", "Ability_IDs", "Core_Ability_IDs", "Weapon_IDs", 'M"', "T", "SV", "W", "LD", "OC", "Keywords", "Hyperlink"]
for index in range(1, 9):
    UNITS_HEADER.extend([f"Points_Label_{index}", f"Points_Cost_{index}"])

PROFILE_NOTES = {
    "Unit_ID": "Stable unique unit key; authoritative parent for unit relationships.",
    "Unit Name": "Visible unit name.",
    'M"': "Unit movement value in the current HTML-compatible display format.",
    "T": "Unit Toughness characteristic.",
    "SV": "Unit save/invulnerable display value in the current HTML-compatible format.",
    "W": "Unit Wounds characteristic.",
    "LD": "Unit Leadership characteristic.",
    "OC": "Unit Objective Control characteristic.",
    "Keywords": "Current HTML-compatible comma-separated unit keywords.",
    "Hyperlink": "Source/reference hyperlink for the unit.",
}
GENERATED_NOTE = "Generated compatibility output from Unit_Profiles.csv, Unit_Abilities.csv, Unit_Weapons.csv, and Unit_Points.csv; do not author directly."


def fail(message):
    raise SystemExit(message)


def read_dicts(path, expected_header):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != expected_header:
            fail(f"{path.relative_to(ROOT)} header mismatch: {reader.fieldnames!r}")
        rows = list(reader)
    return [row for row in rows if any((value or "").strip() for value in row.values())]


def write_dicts(path, header, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def migrate_profiles():
    for army in ARMIES:
        directory = ROOT / "data" / army
        units = read_dicts(directory / "Units.csv", UNITS_HEADER)
        expected = [{column: row.get(column, "") for column in PROFILE_HEADER} for row in units]
        path = directory / "Unit_Profiles.csv"
        if path.exists():
            if read_dicts(path, PROFILE_HEADER) != expected:
                fail(f"{army}: existing Unit_Profiles.csv differs from current Units.csv profile fields")
            print(f"{army}: Unit_Profiles.csv current ({len(expected)} profiles)")
        else:
            write_dicts(path, PROFILE_HEADER, expected)
            print(f"{army}: created Unit_Profiles.csv ({len(expected)} profiles)")


def migrate_schema():
    path = ROOT / "data" / "CSV_SCHEMA.csv"
    header = ["Scope", "File", "Column_Order", "Column_Name", "Required", "Ownership", "Notes"]
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != header:
            fail("unexpected CSV_SCHEMA.csv header")
        rows = list(reader)
    if any((row.get("File") or "").strip() == "Unit_Profiles.csv" for row in rows):
        print("CSV_SCHEMA.csv already migrated")
        return

    profile_rows = [{
        "Scope": "army",
        "File": "Unit_Profiles.csv",
        "Column_Order": str(index),
        "Column_Name": column,
        "Required": "YES" if column in {"Unit_ID", "Unit Name"} else "NO",
        "Ownership": "AUTHORITATIVE",
        "Notes": PROFILE_NOTES[column],
    } for index, column in enumerate(PROFILE_HEADER, start=1)]

    foreign_key_files = {
        "Unit_Abilities.csv", "Unit_Weapons.csv", "Unit_Points.csv", "Unit_Loadout_Options.csv",
        "Unit_Loadout_Weapons.csv", "Unit_Loadout_Abilities.csv", "Unit_Loadout_Points.csv",
        "Unit_Loadout_Compatibility.csv", "Unit_Loadout_Legacy_Units.csv",
    }
    output = []
    inserted = False
    for row in rows:
        file_name = (row.get("File") or "").strip()
        if file_name == "Units.csv" and not inserted:
            output.extend(profile_rows)
            inserted = True
        row = dict(row)
        if file_name == "Units.csv":
            row["Ownership"] = "GENERATED_COMPAT"
            row["Notes"] = GENERATED_NOTE
        elif file_name in foreign_key_files:
            row["Notes"] = (row.get("Notes") or "").replace("Foreign key to Units.csv.", "Foreign key to Unit_Profiles.csv.")
        output.append(row)
    if not inserted:
        fail("Units.csv is missing from CSV_SCHEMA.csv")
    write_dicts(path, header, output)
    print("CSV_SCHEMA.csv: Unit_Profiles authoritative; Units generated compatibility")


def patch_split_units():
    path = ROOT / "scripts" / "split_units_v1.py"
    text = path.read_text(encoding="utf-8")
    if "PROFILE_HEADER = [" not in text:
        marker = 'UNITS_HEADER = [\n'
        profile = '''PROFILE_HEADER = [\n    "Unit_ID",\n    "Unit Name",\n    'M"',\n    "T",\n    "SV",\n    "W",\n    "LD",\n    "OC",\n    "Keywords",\n    "Hyperlink",\n]\n\n'''
        if marker not in text:
            fail("cannot add PROFILE_HEADER to split_units_v1.py")
        text = text.replace(marker, profile + marker, 1)

    start = text.find("def sync_army(army):")
    end = text.find("\ndef main():", start)
    if start < 0 or end < 0:
        fail("cannot locate sync_army in split_units_v1.py")
    replacement = '''def sync_army(army):\n    directory = ROOT / "data" / army\n    units_path = directory / "Units.csv"\n    profiles = read_dict_rows(directory / "Unit_Profiles.csv", PROFILE_HEADER)\n    abilities = read_dict_rows(directory / "Unit_Abilities.csv", UNIT_ABILITIES_HEADER)\n    weapons = read_dict_rows(directory / "Unit_Weapons.csv", UNIT_WEAPONS_HEADER)\n    points = read_dict_rows(directory / "Unit_Points.csv", UNIT_POINTS_HEADER)\n\n    unit_id_set = set()\n    for line_no, profile in enumerate(profiles, start=2):\n        unit_id = (profile.get("Unit_ID") or "").strip()\n        if not unit_id:\n            fail(f"{army}: blank Unit_ID at Unit_Profiles.csv line {line_no}")\n        if unit_id in unit_id_set:\n            fail(f"{army}: duplicate Unit_ID {unit_id!r} in Unit_Profiles.csv")\n        unit_id_set.add(unit_id)\n\n    ability_map = {}\n    core_ability_map = {}\n    weapon_map = {}\n    point_map = {}\n\n    for line_no, row in enumerate(abilities, start=2):\n        unit_id = (row.get("Unit_ID") or "").strip()\n        ability_id = (row.get("Ability_ID") or "").strip()\n        ability_type = (row.get("Ability_Type") or "").strip().upper()\n        if unit_id not in unit_id_set:\n            fail(f"{army}: Unit_Abilities line {line_no} references missing Unit_Profile {unit_id!r}")\n        if not ability_id:\n            fail(f"{army}: blank Ability_ID in Unit_Abilities line {line_no}")\n        if ability_type == "ABILITY":\n            add_unique(ability_map, unit_id, ability_id, "unit ability", army)\n        elif ability_type == "CORE_ABILITY":\n            add_unique(core_ability_map, unit_id, ability_id, "unit core ability", army)\n        else:\n            fail(f"{army}: unsupported Ability_Type {ability_type!r} in Unit_Abilities line {line_no}")\n\n    for line_no, row in enumerate(weapons, start=2):\n        unit_id = (row.get("Unit_ID") or "").strip()\n        weapon_id = (row.get("Weapon_ID") or "").strip()\n        if unit_id not in unit_id_set:\n            fail(f"{army}: Unit_Weapons line {line_no} references missing Unit_Profile {unit_id!r}")\n        if not weapon_id:\n            fail(f"{army}: blank Weapon_ID in Unit_Weapons line {line_no}")\n        add_unique(weapon_map, unit_id, weapon_id, "unit weapon", army)\n\n    for line_no, row in enumerate(points, start=2):\n        unit_id = (row.get("Unit_ID") or "").strip()\n        if unit_id not in unit_id_set:\n            fail(f"{army}: Unit_Points line {line_no} references missing Unit_Profile {unit_id!r}")\n        slot = point_slot(row, army)\n        slots = point_map.setdefault(unit_id, {})\n        if slot in slots:\n            fail(f"{army}: duplicate Unit_Points slot {slot} for {unit_id!r}")\n        slots[slot] = {"label": row.get("Label") or "", "cost": row.get("Cost") or ""}\n\n    units = []\n    for profile in profiles:\n        unit_id = (profile.get("Unit_ID") or "").strip()\n        unit = {column: "" for column in UNITS_HEADER}\n        for column in PROFILE_HEADER:\n            unit[column] = profile.get(column) or ""\n        unit["Ability_IDs"] = ", ".join(ability_map.get(unit_id, []))\n        unit["Core_Ability_IDs"] = ", ".join(core_ability_map.get(unit_id, []))\n        unit["Weapon_IDs"] = ", ".join(weapon_map.get(unit_id, []))\n        for index, point in point_map.get(unit_id, {}).items():\n            unit[f"Points_Label_{index}"] = point["label"]\n            unit[f"Points_Cost_{index}"] = point["cost"]\n        units.append(unit)\n\n    current = read_dict_rows(units_path, UNITS_HEADER) if units_path.exists() else []\n    changed = current != units\n    if changed:\n        write_units(units_path, units)\n\n    print(\n        f"{army}: {len(units)} generated units <- Unit_Profiles + "\n        f"{len(abilities)} ability links, {len(weapons)} weapon links, {len(points)} point options "\n        f"({'updated' if changed else 'current'})"\n    )\n'''
    text = text[:start] + replacement + text[end:]
    text = text.replace('print("normalized unit compatibility sync: OK")', 'print("authoritative Unit_Profiles -> legacy Units compatibility sync: OK")')
    path.write_text(text, encoding="utf-8")
    print("scripts/split_units_v1.py: Unit_Profiles is now authoritative")


def patch_validator():
    path = ROOT / "scripts" / "validate_unit_relations.py"
    text = path.read_text(encoding="utf-8")
    if "PROFILE_HEADER = [" not in text:
        marker = 'UNIT_ABILITIES_HEADER = ["Unit_ID", "Ability_ID", "Ability_Type"]\n'
        profile = '''PROFILE_HEADER = ["Unit_ID", "Unit Name", 'M"', "T", "SV", "W", "LD", "OC", "Keywords", "Hyperlink"]\n\n'''
        if marker not in text:
            fail("cannot add PROFILE_HEADER to validate_unit_relations.py")
        text = text.replace(marker, profile + marker, 1)

    text = text.replace(
        '    units = read_dicts(directory / "Units.csv")\n',
        '    profiles = read_dicts(directory / "Unit_Profiles.csv", PROFILE_HEADER)\n    units = read_dicts(directory / "Units.csv")\n',
        1,
    )
    text = text.replace(
        '    unit_ids = {(row.get("Unit_ID") or "").strip() for row in units}\n    unit_rank = {\n        (row.get("Unit_ID") or "").strip(): index\n        for index, row in enumerate(units)\n    }\n',
        '    require_unique(profiles, ["Unit_ID"], "unit profile", army)\n    unit_ids = {(row.get("Unit_ID") or "").strip() for row in profiles}\n    unit_rank = {\n        (row.get("Unit_ID") or "").strip(): index\n        for index, row in enumerate(profiles)\n    }\n    if len(units) != len(profiles):\n        fail(f"{army}: Units.csv row count does not match Unit_Profiles.csv")\n    for index, (profile, unit) in enumerate(zip(profiles, units), start=2):\n        for column in PROFILE_HEADER:\n            if (unit.get(column) or "") != (profile.get(column) or ""):\n                fail(f"{army}: Units.csv line {index} profile column {column!r} differs from Unit_Profiles.csv")\n',
        1,
    )
    text = text.replace("references missing Unit_ID", "references missing Unit_Profile")
    text = text.replace("unit relationship validation: OK", "authoritative unit profile and relationship validation: OK")
    path.write_text(text, encoding="utf-8")
    print("scripts/validate_unit_relations.py: added Unit_Profiles parity validation")


def patch_data_schema():
    path = ROOT / "scripts" / "data_schema.py"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        '        units = loaded[(army, "Units.csv")]\n        weapons = loaded[(army, "Weapon_Stats.csv")]',
        '        unit_profiles = loaded[(army, "Unit_Profiles.csv")]\n        units = loaded[(army, "Units.csv")]\n        weapons = loaded[(army, "Weapon_Stats.csv")]',
        1,
    )
    text = text.replace(
        '        require_unique(units, ["Unit_ID"], f"{army} Unit_ID")',
        '        require_unique(unit_profiles, ["Unit_ID"], f"{army} authoritative Unit_ID")\n        require_unique(units, ["Unit_ID"], f"{army} generated Unit_ID")',
        1,
    )
    text = text.replace(
        '        unit_ids = {(row["Unit_ID"] or "").strip() for _, row in units}\n        weapon_ids =',
        '        unit_ids = {(row["Unit_ID"] or "").strip() for _, row in unit_profiles}\n        generated_unit_ids = {(row["Unit_ID"] or "").strip() for _, row in units}\n        if generated_unit_ids != unit_ids:\n            fail(f"{army}: Units.csv Unit_ID set does not match authoritative Unit_Profiles.csv")\n        weapon_ids =',
        1,
    )
    if 'unit_profiles = loaded[(army, "Unit_Profiles.csv")]' not in text or "generated_unit_ids != unit_ids" not in text:
        fail("data_schema.py Unit_Profiles patch did not apply")
    path.write_text(text, encoding="utf-8")
    print("scripts/data_schema.py: authoritative unit identity now comes from Unit_Profiles.csv")


def main():
    migrate_profiles()
    migrate_schema()
    patch_split_units()
    patch_validator()
    patch_data_schema()
    print("Unit_Profiles authority migration: OK")


if __name__ == "__main__":
    main()
