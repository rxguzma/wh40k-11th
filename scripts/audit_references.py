#!/usr/bin/env python3
from data_schema import ARMIES, ROOT, load_dict_rows, load_schema


def main():
    schemas, _ = load_schema()
    universal_path = ROOT / "data" / "universal" / "Universal_Abilities.csv"
    universal_rows = load_dict_rows(universal_path, schemas[("universal", "Universal_Abilities.csv")])
    universal_abilities = {(row["Ability_ID"] or "").strip() for _, row in universal_rows}
    errors = []

    for army in ARMIES:
        base = ROOT / "data" / army
        profiles = load_dict_rows(base / "Unit_Profiles.csv", schemas[("army", "Unit_Profiles.csv")])
        weapons = load_dict_rows(base / "Weapon_Stats.csv", schemas[("army", "Weapon_Stats.csv")])
        abilities = load_dict_rows(base / "Abilities.csv", schemas[("army", "Abilities.csv")])
        unit_abilities = load_dict_rows(base / "Unit_Abilities.csv", schemas[("army", "Unit_Abilities.csv")])
        unit_weapons = load_dict_rows(base / "Unit_Weapons.csv", schemas[("army", "Unit_Weapons.csv")])
        unit_points = load_dict_rows(base / "Unit_Points.csv", schemas[("army", "Unit_Points.csv")])
        weapon_abilities = load_dict_rows(base / "Weapon_Abilities.csv", schemas[("army", "Weapon_Abilities.csv")])
        loadout_options = load_dict_rows(base / "Loadout_Options.csv", schemas[("army", "Loadout_Options.csv")])
        loadout_weapons = load_dict_rows(base / "Loadout_Weapons.csv", schemas[("army", "Loadout_Weapons.csv")])
        loadout_abilities = load_dict_rows(base / "Loadout_Abilities.csv", schemas[("army", "Loadout_Abilities.csv")])
        loadout_points = load_dict_rows(base / "Loadout_Points.csv", schemas[("army", "Loadout_Points.csv")])
        loadout_compatibility = load_dict_rows(
            base / "Loadout_Compatibility.csv", schemas[("army", "Loadout_Compatibility.csv")]
        )

        unit_ids = {(row["Unit_ID"] or "").strip() for _, row in profiles}
        weapon_ids = {(row["Weapon_ID"] or "").strip() for _, row in weapons}
        ability_ids = {(row["Ability_ID"] or "").strip() for _, row in abilities} | universal_abilities
        loadout_option_ids = {(row["Loadout_Option_ID"] or "").strip() for _, row in loadout_options}

        for line_no, row in unit_abilities:
            unit_id = (row["Unit_ID"] or "").strip()
            ability_id = (row["Ability_ID"] or "").strip()
            if unit_id not in unit_ids:
                errors.append(f"{army},Unit_Abilities.csv,{line_no},{ability_id},Unit_ID,{unit_id}")
            if ability_id not in ability_ids:
                errors.append(f"{army},Unit_Abilities.csv,{line_no},{unit_id},Ability_ID,{ability_id}")

        for line_no, row in unit_weapons:
            unit_id = (row["Unit_ID"] or "").strip()
            weapon_id = (row["Weapon_ID"] or "").strip()
            if unit_id not in unit_ids:
                errors.append(f"{army},Unit_Weapons.csv,{line_no},{weapon_id},Unit_ID,{unit_id}")
            if weapon_id not in weapon_ids:
                errors.append(f"{army},Unit_Weapons.csv,{line_no},{unit_id},Weapon_ID,{weapon_id}")

        for line_no, row in unit_points:
            unit_id = (row["Unit_ID"] or "").strip()
            option_id = (row["Point_Option_ID"] or "").strip()
            if unit_id not in unit_ids:
                errors.append(f"{army},Unit_Points.csv,{line_no},{option_id},Unit_ID,{unit_id}")

        for line_no, row in weapon_abilities:
            weapon_id = (row["Weapon_ID"] or "").strip()
            relation_id = (row["Weapon_Ability_ID"] or "").strip()
            if weapon_id not in weapon_ids:
                errors.append(f"{army},Weapon_Abilities.csv,{line_no},{relation_id},Weapon_ID,{weapon_id}")

        for line_no, row in loadout_options:
            unit_id = (row["Unit_ID"] or "").strip()
            lid = (row["Loadout_Option_ID"] or "").strip()
            if unit_id not in unit_ids:
                errors.append(f"{army},Loadout_Options.csv,{line_no},{lid},Unit_ID,{unit_id}")

        for file_name, rows, extra in (
            ("Loadout_Weapons.csv", loadout_weapons, ("Weapon_ID", weapon_ids)),
            ("Loadout_Abilities.csv", loadout_abilities, ("Ability_ID", ability_ids)),
            ("Loadout_Points.csv", loadout_points, None),
            ("Loadout_Compatibility.csv", loadout_compatibility, None),
        ):
            for line_no, row in rows:
                lid = (row["Loadout_Option_ID"] or "").strip()
                if lid not in loadout_option_ids:
                    errors.append(f"{army},{file_name},{line_no},{lid},Loadout_Option_ID,{lid}")
                if extra:
                    column, allowed = extra
                    value = (row.get(column) or "").strip()
                    if value not in allowed:
                        errors.append(f"{army},{file_name},{line_no},{lid},{column},{value}")

    print("reference audit: army,file,line,row,column,missing_reference")
    for error in errors:
        print(error)
    print(f"reference audit total: {len(errors)}")


if __name__ == "__main__":
    main()
