#!/usr/bin/env python3
from collections import defaultdict

from data_schema import ARMIES, ROOT, load_dict_rows, load_schema, split_ids


def main():
    schemas, _ = load_schema()
    universal_path = ROOT / "data" / "universal" / "Universal_Abilities.csv"
    universal_rows = load_dict_rows(universal_path, schemas[("universal", "Universal_Abilities.csv")])
    universal_abilities = {(row["Ability_ID"] or "").strip() for _, row in universal_rows}
    errors = []

    for army in ARMIES:
        base = ROOT / "data" / army
        units = load_dict_rows(base / "Units.csv", schemas[("army", "Units.csv")])
        weapons = load_dict_rows(base / "Weapon_Stats.csv", schemas[("army", "Weapon_Stats.csv")])
        abilities = load_dict_rows(base / "Abilities.csv", schemas[("army", "Abilities.csv")])
        options = load_dict_rows(base / "Unit_Weapon_Options.csv", schemas[("army", "Unit_Weapon_Options.csv")])

        unit_ids = {(row["Unit_ID"] or "").strip() for _, row in units}
        weapon_ids = {(row["Weapon_ID"] or "").strip() for _, row in weapons}
        ability_ids = {(row["Ability_ID"] or "").strip() for _, row in abilities} | universal_abilities

        for line_no, row in units:
            unit_id = (row["Unit_ID"] or "").strip()
            for ref in split_ids(row.get("Weapon_IDs")):
                if ref not in weapon_ids:
                    errors.append(f"{army},Units.csv,{line_no},{unit_id},Weapon_IDs,{ref}")
            for column in ("Ability_IDs", "Core_Ability_IDs"):
                for ref in split_ids(row.get(column)):
                    if ref not in ability_ids:
                        errors.append(f"{army},Units.csv,{line_no},{unit_id},{column},{ref}")

        groups = defaultdict(set)
        for _, row in options:
            groups[((row["Unit_ID"] or "").strip(), (row["Option_Group_ID"] or "").strip())].add((row["Option_ID"] or "").strip())

        for line_no, row in options:
            option_id = (row["Option_ID"] or "").strip()
            unit_id = (row["Unit_ID"] or "").strip()
            if unit_id not in unit_ids:
                errors.append(f"{army},Unit_Weapon_Options.csv,{line_no},{option_id},Unit_ID,{unit_id}")
            for column in ("Weapon_IDs", "Preserve_Weapon_IDs"):
                for ref in split_ids(row.get(column)):
                    if ref not in weapon_ids:
                        errors.append(f"{army},Unit_Weapon_Options.csv,{line_no},{option_id},{column},{ref}")
            for ref in split_ids(row.get("Ability_IDs")):
                if ref not in ability_ids:
                    errors.append(f"{army},Unit_Weapon_Options.csv,{line_no},{option_id},Ability_IDs,{ref}")

    print("reference audit: army,file,line,row,column,missing_reference")
    for error in errors:
        print(error)
    print(f"reference audit total: {len(errors)}")


if __name__ == "__main__":
    main()
