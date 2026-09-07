#!/usr/bin/env python3
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "nids"
OLD_IDS = {"TYRANT_GUARD_BONE_CLEAVER", "TYRANT_GUARD_CLAWS"}
NEW_ID = "TYRANT_GUARD"


def read_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames, list(reader)


def write_rows(path, header, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def replace_unit_rows(path, new_rows):
    header, rows = read_rows(path)
    out = []
    inserted = False
    for row in rows:
        unit_id = (row.get("Unit_ID") or "").strip()
        if unit_id in OLD_IDS:
            if not inserted:
                out.extend(new_rows)
                inserted = True
            continue
        if unit_id == NEW_ID:
            if not inserted:
                out.extend(new_rows)
                inserted = True
            continue
        out.append(row)
    if not inserted:
        out.extend(new_rows)
    write_rows(path, header, out)


def upsert_weapon_stats():
    path = DATA / "Weapon_Stats.csv"
    header, rows = read_rows(path)
    desired = {
        "BONE_CLEAVER_WITH_LASH_WHIP_AND_RENDING_CLAWS": {
            "Weapon_ID": "BONE_CLEAVER_WITH_LASH_WHIP_AND_RENDING_CLAWS",
            "Weapon Name": "Bone cleaver, lash whip and rending claws",
            'R"': "-", "A": "3", "WS": "3", "St": "5", "AP": "-1", "D": "2", "Weapon Abilities": "",
        },
        "CRUSHING_CLAWS_AND_RENDING_CLAWS": {
            "Weapon_ID": "CRUSHING_CLAWS_AND_RENDING_CLAWS",
            "Weapon Name": "Crushing claws and rending claws",
            'R"': "-", "A": "2", "WS": "4", "St": "8", "AP": "-2", "D": "2", "Weapon Abilities": "TWIN-LINKED",
        },
        "SCYTHING_TALONS_AND_RENDING_CLAWS": {
            "Weapon_ID": "SCYTHING_TALONS_AND_RENDING_CLAWS",
            "Weapon Name": "Scything talons and rending claws",
            'R"': "-", "A": "5", "WS": "3", "St": "5", "AP": "-1", "D": "1", "Weapon Abilities": "",
        },
    }
    seen = set()
    out = []
    for row in rows:
        weapon_id = (row.get("Weapon_ID") or "").strip()
        if weapon_id in desired:
            if weapon_id not in seen:
                out.append(desired[weapon_id])
                seen.add(weapon_id)
            continue
        out.append(row)
    for weapon_id, row in desired.items():
        if weapon_id not in seen:
            out.append(row)
    write_rows(path, header, out)


def add_loadout_options():
    path = DATA / "Unit_Loadout_Options.csv"
    header, rows = read_rows(path)
    rows = [r for r in rows if (r.get("Unit_ID") or "").strip() not in OLD_IDS | {NEW_ID}]
    rows.extend([
        {"Unit_ID": NEW_ID, "Option_Group_ID": "TYRANT_GUARD_WEAPON", "Group_Label": "Melee Weapon", "Option_ID": "TYRANT_GUARD_CRUSHING_CLAWS", "Option_Name": "Crushing Claws", "Default": "TRUE", "Sort_Order": "1"},
        {"Unit_ID": NEW_ID, "Option_Group_ID": "TYRANT_GUARD_WEAPON", "Group_Label": "Melee Weapon", "Option_ID": "TYRANT_GUARD_BONE_CLEAVER", "Option_Name": "Bone Cleaver", "Default": "FALSE", "Sort_Order": "2"},
        {"Unit_ID": NEW_ID, "Option_Group_ID": "TYRANT_GUARD_WEAPON", "Group_Label": "Melee Weapon", "Option_ID": "TYRANT_GUARD_SCYTHING_TALONS", "Option_Name": "Scything Talons", "Default": "FALSE", "Sort_Order": "3"},
    ])
    write_rows(path, header, rows)


def add_loadout_weapons():
    path = DATA / "Unit_Loadout_Weapons.csv"
    header, rows = read_rows(path)
    rows = [r for r in rows if (r.get("Unit_ID") or "").strip() not in OLD_IDS | {NEW_ID}]
    rows.extend([
        {"Unit_ID": NEW_ID, "Option_Group_ID": "TYRANT_GUARD_WEAPON", "Option_ID": "TYRANT_GUARD_CRUSHING_CLAWS", "Weapon_ID": "CRUSHING_CLAWS_AND_RENDING_CLAWS", "Weapon_Role": "SELECTED", "Sort_Order": "1"},
        {"Unit_ID": NEW_ID, "Option_Group_ID": "TYRANT_GUARD_WEAPON", "Option_ID": "TYRANT_GUARD_BONE_CLEAVER", "Weapon_ID": "BONE_CLEAVER_WITH_LASH_WHIP_AND_RENDING_CLAWS", "Weapon_Role": "SELECTED", "Sort_Order": "1"},
        {"Unit_ID": NEW_ID, "Option_Group_ID": "TYRANT_GUARD_WEAPON", "Option_ID": "TYRANT_GUARD_SCYTHING_TALONS", "Weapon_ID": "SCYTHING_TALONS_AND_RENDING_CLAWS", "Weapon_Role": "SELECTED", "Sort_Order": "1"},
    ])
    write_rows(path, header, rows)


def remove_old_ids_from_other_loadout_tables():
    for name in ["Unit_Loadout_Abilities.csv", "Unit_Loadout_Points.csv", "Unit_Loadout_Compatibility.csv", "Unit_Loadout_Legacy_Units.csv"]:
        path = DATA / name
        header, rows = read_rows(path)
        filtered = [r for r in rows if (r.get("Unit_ID") or "").strip() not in OLD_IDS]
        write_rows(path, header, filtered)


def main():
    replace_unit_rows(DATA / "Unit_Profiles.csv", [{
        "Unit_ID": NEW_ID,
        "Unit Name": "Tyrant Guard",
        'M"': '6"',
        "T": "8",
        "SV": "3+",
        "W": "4",
        "LD": "8",
        "OC": "1",
        "Keywords": "INFANTRY, GREAT DEVOURER, TYRANT GUARD",
        "Hyperlink": "https://wahapedia.ru/wh40k11ed/factions/tyranids/Tyrant-Guard",
    }])

    replace_unit_rows(DATA / "Unit_Abilities.csv", [{
        "Unit_ID": NEW_ID, "Ability_ID": "GUARDIAN_ORGANISM", "Ability_Type": "ABILITY"
    }])

    replace_unit_rows(DATA / "Unit_Weapons.csv", [
        {"Unit_ID": NEW_ID, "Weapon_ID": "CRUSHING_CLAWS_AND_RENDING_CLAWS"},
        {"Unit_ID": NEW_ID, "Weapon_ID": "BONE_CLEAVER_WITH_LASH_WHIP_AND_RENDING_CLAWS"},
        {"Unit_ID": NEW_ID, "Weapon_ID": "SCYTHING_TALONS_AND_RENDING_CLAWS"},
    ])

    replace_unit_rows(DATA / "Unit_Points.csv", [
        {"Unit_ID": NEW_ID, "Point_Option_ID": "point_1", "Label": "x3", "Cost": "80", "Sort_Order": "1"},
        {"Unit_ID": NEW_ID, "Point_Option_ID": "point_2", "Label": "x6", "Cost": "170", "Sort_Order": "2"},
    ])

    upsert_weapon_stats()
    add_loadout_options()
    add_loadout_weapons()
    remove_old_ids_from_other_loadout_tables()

    print("Tyrant Guard consolidated to TYRANT_GUARD with Crushing Claws default; no legacy unit alias created.")


if __name__ == "__main__":
    main()
