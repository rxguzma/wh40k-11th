#!/usr/bin/env python3
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMIES = ("marines", "orks", "nids")

OLD_HEADERS = {
    "Unit_Loadout_Options.csv": ["Unit_ID","Option_Group_ID","Group_Label","Option_ID","Option_Name","Default","Sort_Order"],
    "Unit_Loadout_Weapons.csv": ["Unit_ID","Option_Group_ID","Option_ID","Weapon_ID","Weapon_Role","Sort_Order"],
    "Unit_Loadout_Abilities.csv": ["Unit_ID","Option_Group_ID","Option_ID","Ability_ID","Sort_Order"],
    "Unit_Loadout_Points.csv": ["Unit_ID","Option_Group_ID","Option_ID","Point_Option_ID","Label","Cost","Sort_Order"],
    "Unit_Loadout_Compatibility.csv": ["Unit_ID","Option_Group_ID","Option_ID","Required_Group_ID","Compatible_Option_ID","Rule_Order","Option_Order"],
    "Unit_Loadout_Legacy_Units.csv": ["Unit_ID","Option_Group_ID","Option_ID","Legacy_Unit_ID","Sort_Order"],
}

NEW_HEADERS = {
    "Loadout_Options.csv": ["Loadout_Option_ID","Unit_ID","Option_Group_ID","Group_Label","Option_ID","Option_Name","Default","Sort_Order"],
    "Loadout_Weapons.csv": ["Loadout_Option_ID","Weapon_ID","Weapon_Role","Sort_Order"],
    "Loadout_Abilities.csv": ["Loadout_Option_ID","Ability_ID","Sort_Order"],
    "Loadout_Points.csv": ["Loadout_Option_ID","Point_Option_ID","Label","Cost","Sort_Order"],
    "Loadout_Compatibility.csv": ["Loadout_Option_ID","Required_Group_ID","Compatible_Option_ID","Rule_Order","Option_Order"],
    "Loadout_Legacy_Units.csv": ["Loadout_Option_ID","Legacy_Unit_ID","Sort_Order"],
}

SPLIT_LOADOUTS = '#!/usr/bin/env python3\nimport csv\nfrom collections import defaultdict\nfrom pathlib import Path\n\nROOT = Path(__file__).resolve().parents[1]\nARMIES = ("marines", "orks", "nids")\nTRUE_VALUES = {"true", "1", "yes", "y"}\n\nLEGACY_HEADER = [\n    "Unit_ID", "Option_Group_ID", "Group_Label", "Option_ID", "Option_Name",\n    "Weapon_IDs", "Ability_IDs", "Points_Label_1", "Points_Cost_1",\n    "Points_Label_2", "Points_Cost_2", "Default", "Sort_Order",\n    "Legacy_Unit_IDs", "Preserve_Weapon_IDs", "Compatible_With",\n]\nCANON_OPTIONS_HEADER = [\n    "Loadout_Option_ID", "Unit_ID", "Option_Group_ID", "Group_Label", "Option_ID",\n    "Option_Name", "Default", "Sort_Order",\n]\nCANON_WEAPONS_HEADER = ["Loadout_Option_ID", "Weapon_ID", "Weapon_Role", "Sort_Order"]\nCANON_ABILITIES_HEADER = ["Loadout_Option_ID", "Ability_ID", "Sort_Order"]\nCANON_POINTS_HEADER = ["Loadout_Option_ID", "Point_Option_ID", "Label", "Cost", "Sort_Order"]\nCANON_COMPAT_HEADER = [\n    "Loadout_Option_ID", "Required_Group_ID", "Compatible_Option_ID", "Rule_Order", "Option_Order",\n]\nCANON_LEGACY_UNITS_HEADER = ["Loadout_Option_ID", "Legacy_Unit_ID", "Sort_Order"]\n\nCOMPAT_OPTIONS_HEADER = [\n    "Unit_ID", "Option_Group_ID", "Group_Label", "Option_ID", "Option_Name", "Default", "Sort_Order",\n]\nCOMPAT_WEAPONS_HEADER = [\n    "Unit_ID", "Option_Group_ID", "Option_ID", "Weapon_ID", "Weapon_Role", "Sort_Order",\n]\nCOMPAT_ABILITIES_HEADER = ["Unit_ID", "Option_Group_ID", "Option_ID", "Ability_ID", "Sort_Order"]\nCOMPAT_POINTS_HEADER = [\n    "Unit_ID", "Option_Group_ID", "Option_ID", "Point_Option_ID", "Label", "Cost", "Sort_Order",\n]\nCOMPAT_COMPAT_HEADER = [\n    "Unit_ID", "Option_Group_ID", "Option_ID", "Required_Group_ID",\n    "Compatible_Option_ID", "Rule_Order", "Option_Order",\n]\nCOMPAT_LEGACY_UNITS_HEADER = [\n    "Unit_ID", "Option_Group_ID", "Option_ID", "Legacy_Unit_ID", "Sort_Order",\n]\n\n\ndef fail(message):\n    raise SystemExit(message)\n\n\ndef read_dicts(path, expected_header):\n    with path.open(encoding="utf-8-sig", newline="") as handle:\n        reader = csv.DictReader(handle)\n        if reader.fieldnames != expected_header:\n            fail(\n                f"{path.relative_to(ROOT)} header mismatch\\n"\n                f"expected: {expected_header!r}\\n"\n                f"actual:   {reader.fieldnames!r}"\n            )\n        rows = list(reader)\n    return [row for row in rows if any((value or "").strip() for value in row.values())]\n\n\ndef write_csv(path, header, rows):\n    with path.open("w", encoding="utf-8", newline="") as handle:\n        writer = csv.writer(handle, lineterminator="\\n")\n        writer.writerow(header)\n        writer.writerows(rows)\n\n\ndef clean(value):\n    return (value or "").strip()\n\n\ndef order_value(value):\n    text = clean(value)\n    try:\n        return int(text)\n    except ValueError:\n        return 0\n\n\ndef load_canonical(directory):\n    options = read_dicts(directory / "Loadout_Options.csv", CANON_OPTIONS_HEADER)\n    weapons = read_dicts(directory / "Loadout_Weapons.csv", CANON_WEAPONS_HEADER)\n    abilities = read_dicts(directory / "Loadout_Abilities.csv", CANON_ABILITIES_HEADER)\n    points = read_dicts(directory / "Loadout_Points.csv", CANON_POINTS_HEADER)\n    compatibility = read_dicts(directory / "Loadout_Compatibility.csv", CANON_COMPAT_HEADER)\n    legacy_units = read_dicts(directory / "Loadout_Legacy_Units.csv", CANON_LEGACY_UNITS_HEADER)\n    return options, weapons, abilities, points, compatibility, legacy_units\n\n\ndef validate_canonical(army, tables):\n    options, weapons, abilities, points, compatibility, legacy_units = tables\n    by_id = {}\n    group_defaults = defaultdict(int)\n    group_options = defaultdict(set)\n\n    for row in options:\n        lid = clean(row.get("Loadout_Option_ID"))\n        unit_id = clean(row.get("Unit_ID"))\n        group_id = clean(row.get("Option_Group_ID"))\n        option_id = clean(row.get("Option_ID"))\n        option_name = clean(row.get("Option_Name"))\n        if not lid or not unit_id or not group_id or not option_id or not option_name:\n            fail(f"{army}: incomplete canonical loadout option identity")\n        if lid in by_id:\n            fail(f"{army}: duplicate Loadout_Option_ID {lid!r}")\n        semantic_key = (unit_id, group_id, option_id)\n        if semantic_key in {(v["Unit_ID"], v["Option_Group_ID"], v["Option_ID"]) for v in by_id.values()}:\n            fail(f"{army}: duplicate semantic loadout option {semantic_key!r}")\n        by_id[lid] = row\n        group_options[(unit_id, group_id)].add(option_id)\n        if clean(row.get("Default")).lower() in TRUE_VALUES:\n            group_defaults[(unit_id, group_id)] += 1\n\n    for group_key in group_options:\n        if group_defaults[group_key] != 1:\n            fail(f"{army}: {group_key!r} must have exactly one default option")\n\n    for filename, rows in (\n        ("Loadout_Weapons.csv", weapons),\n        ("Loadout_Abilities.csv", abilities),\n        ("Loadout_Points.csv", points),\n        ("Loadout_Compatibility.csv", compatibility),\n        ("Loadout_Legacy_Units.csv", legacy_units),\n    ):\n        for row in rows:\n            lid = clean(row.get("Loadout_Option_ID"))\n            if lid not in by_id:\n                fail(f"{army}: {filename} references missing Loadout_Option_ID {lid!r}")\n\n    for row in compatibility:\n        lid = clean(row["Loadout_Option_ID"])\n        parent = by_id[lid]\n        required_group = clean(row.get("Required_Group_ID"))\n        compatible_option = clean(row.get("Compatible_Option_ID"))\n        if not required_group or compatible_option not in group_options.get((parent["Unit_ID"], required_group), set()):\n            fail(\n                f"{army}: compatibility for {lid!r} references unknown "\n                f"{required_group}/{compatible_option}"\n            )\n    return by_id\n\n\ndef generate_compatibility(army, directory, tables):\n    options, weapons, abilities, points, compatibility, legacy_units = tables\n    by_id = validate_canonical(army, tables)\n\n    def parent(lid):\n        row = by_id[clean(lid)]\n        return row["Unit_ID"], row["Option_Group_ID"], row["Option_ID"]\n\n    compat_options = [\n        [\n            row["Unit_ID"], row["Option_Group_ID"], row["Group_Label"], row["Option_ID"],\n            row["Option_Name"], row["Default"], row["Sort_Order"],\n        ]\n        for row in options\n    ]\n    compat_weapons = [\n        [*parent(row["Loadout_Option_ID"]), row["Weapon_ID"], row["Weapon_Role"], row["Sort_Order"]]\n        for row in weapons\n    ]\n    compat_abilities = [\n        [*parent(row["Loadout_Option_ID"]), row["Ability_ID"], row["Sort_Order"]]\n        for row in abilities\n    ]\n    compat_points = [\n        [\n            *parent(row["Loadout_Option_ID"]), row["Point_Option_ID"], row["Label"],\n            row["Cost"], row["Sort_Order"],\n        ]\n        for row in points\n    ]\n    compat_compatibility = [\n        [\n            *parent(row["Loadout_Option_ID"]), row["Required_Group_ID"],\n            row["Compatible_Option_ID"], row["Rule_Order"], row["Option_Order"],\n        ]\n        for row in compatibility\n    ]\n    compat_legacy_units = [\n        [*parent(row["Loadout_Option_ID"]), row["Legacy_Unit_ID"], row["Sort_Order"]]\n        for row in legacy_units\n    ]\n\n    write_csv(directory / "Unit_Loadout_Options.csv", COMPAT_OPTIONS_HEADER, compat_options)\n    write_csv(directory / "Unit_Loadout_Weapons.csv", COMPAT_WEAPONS_HEADER, compat_weapons)\n    write_csv(directory / "Unit_Loadout_Abilities.csv", COMPAT_ABILITIES_HEADER, compat_abilities)\n    write_csv(directory / "Unit_Loadout_Points.csv", COMPAT_POINTS_HEADER, compat_points)\n    write_csv(directory / "Unit_Loadout_Compatibility.csv", COMPAT_COMPAT_HEADER, compat_compatibility)\n    write_csv(directory / "Unit_Loadout_Legacy_Units.csv", COMPAT_LEGACY_UNITS_HEADER, compat_legacy_units)\n\n    return (\n        [dict(zip(COMPAT_OPTIONS_HEADER, row)) for row in compat_options],\n        [dict(zip(COMPAT_WEAPONS_HEADER, row)) for row in compat_weapons],\n        [dict(zip(COMPAT_ABILITIES_HEADER, row)) for row in compat_abilities],\n        [dict(zip(COMPAT_POINTS_HEADER, row)) for row in compat_points],\n        [dict(zip(COMPAT_COMPAT_HEADER, row)) for row in compat_compatibility],\n        [dict(zip(COMPAT_LEGACY_UNITS_HEADER, row)) for row in compat_legacy_units],\n    )\n\n\ndef generate_legacy(army, directory, compat_tables):\n    options, weapons, abilities, points, compatibility, legacy_units = compat_tables\n\n    option_keys = set()\n    group_options = defaultdict(set)\n    for row in options:\n        key = (clean(row["Unit_ID"]), clean(row["Option_Group_ID"]), clean(row["Option_ID"]))\n        option_keys.add(key)\n        group_options[(key[0], key[1])].add(key[2])\n\n    selected_weapons = defaultdict(list)\n    preserved_weapons = defaultdict(list)\n    ability_links = defaultdict(list)\n    point_links = defaultdict(list)\n    compatibility_links = defaultdict(list)\n    legacy_links = defaultdict(list)\n\n    for source_index, row in enumerate(weapons):\n        key = (clean(row["Unit_ID"]), clean(row["Option_Group_ID"]), clean(row["Option_ID"]))\n        record = (order_value(row["Sort_Order"]), source_index, clean(row["Weapon_ID"]))\n        target = preserved_weapons if clean(row["Weapon_Role"]).upper() == "PRESERVE" else selected_weapons\n        target[key].append(record)\n\n    for source_index, row in enumerate(abilities):\n        key = (clean(row["Unit_ID"]), clean(row["Option_Group_ID"]), clean(row["Option_ID"]))\n        ability_links[key].append((order_value(row["Sort_Order"]), source_index, clean(row["Ability_ID"])))\n\n    for source_index, row in enumerate(points):\n        key = (clean(row["Unit_ID"]), clean(row["Option_Group_ID"]), clean(row["Option_ID"]))\n        point_id = clean(row["Point_Option_ID"])\n        sort_order = order_value(row["Sort_Order"])\n        slot = 0\n        if point_id.lower().startswith("point_"):\n            try:\n                slot = int(point_id.split("_", 1)[1])\n            except ValueError:\n                slot = 0\n        if slot not in (1, 2):\n            slot = sort_order if sort_order in (1, 2) else 0\n        if slot not in (1, 2):\n            fail(f"{army}: legacy Unit_Weapon_Options.csv cannot represent point slot {point_id!r} for {key!r}")\n        if any(existing[0] == slot for existing in point_links[key]):\n            fail(f"{army}: duplicate loadout point slot {slot} for {key!r}")\n        point_links[key].append((slot, source_index, clean(row["Label"]), clean(row["Cost"])))\n\n    for source_index, row in enumerate(compatibility):\n        key = (clean(row["Unit_ID"]), clean(row["Option_Group_ID"]), clean(row["Option_ID"]))\n        compatibility_links[key].append((\n            order_value(row["Rule_Order"]) or 1,\n            clean(row["Required_Group_ID"]),\n            order_value(row["Option_Order"]) or 1,\n            source_index,\n            clean(row["Compatible_Option_ID"]),\n        ))\n\n    for source_index, row in enumerate(legacy_units):\n        key = (clean(row["Unit_ID"]), clean(row["Option_Group_ID"]), clean(row["Option_ID"]))\n        legacy_links[key].append((order_value(row["Sort_Order"]), source_index, clean(row["Legacy_Unit_ID"])))\n\n    legacy_rows = []\n    for option in options:\n        key = (clean(option["Unit_ID"]), clean(option["Option_Group_ID"]), clean(option["Option_ID"]))\n        selected = ", ".join(item[2] for item in sorted(selected_weapons[key]))\n        preserved = ", ".join(item[2] for item in sorted(preserved_weapons[key]))\n        granted = ", ".join(item[2] for item in sorted(ability_links[key]))\n        aliases = ", ".join(item[2] for item in sorted(legacy_links[key]))\n        point_slots = {slot: (label, cost) for slot, _, label, cost in point_links[key]}\n\n        compat_groups = {}\n        compat_order = []\n        for rule_order, required_group, option_order, source_index, compatible_option in sorted(compatibility_links[key]):\n            group_key = (rule_order, required_group)\n            if group_key not in compat_groups:\n                compat_groups[group_key] = []\n                compat_order.append(group_key)\n            compat_groups[group_key].append((option_order, source_index, compatible_option))\n        compatible_with = ";".join(\n            f"{required_group}=" + "|".join(item[2] for item in sorted(compat_groups[(rule_order, required_group)]))\n            for rule_order, required_group in compat_order\n        )\n\n        point_1 = point_slots.get(1, ("", ""))\n        point_2 = point_slots.get(2, ("", ""))\n        legacy_rows.append([\n            key[0], key[1], clean(option["Group_Label"]), key[2], clean(option["Option_Name"]),\n            selected, granted, point_1[0], point_1[1], point_2[0], point_2[1],\n            clean(option["Default"]), clean(option["Sort_Order"]), aliases, preserved, compatible_with,\n        ])\n\n    write_csv(directory / "Unit_Weapon_Options.csv", LEGACY_HEADER, legacy_rows)\n\n\ndef migrate_army(army):\n    directory = ROOT / "data" / army\n    tables = load_canonical(directory)\n    compat_tables = generate_compatibility(army, directory, tables)\n    generate_legacy(army, directory, compat_tables)\n    options, weapons, abilities, points, compatibility, legacy_units = tables\n    print(\n        f"{army}: {len(options)} canonical Loadout_Option_ID rows -> compatibility tables "\n        f"({len(weapons)} weapon links, {len(abilities)} ability links, {len(points)} point rows, "\n        f"{len(compatibility)} compatibility rows, {len(legacy_units)} legacy aliases)"\n    )\n\n\ndef main():\n    for army in ARMIES:\n        migrate_army(army)\n    print("canonical Loadout_Option_ID -> Unit_Loadout_* compatibility sync: OK")\n\n\nif __name__ == "__main__":\n    main()\n'
VALIDATE_LOADOUTS = '#!/usr/bin/env python3\nimport csv\nfrom collections import defaultdict\nfrom pathlib import Path\n\nROOT = Path(__file__).resolve().parents[1]\nARMIES = ("marines", "orks", "nids")\nTRUE_VALUES = {"true", "1", "yes", "y"}\n\nCANON = {\n    "Loadout_Options.csv": [\n        "Loadout_Option_ID", "Unit_ID", "Option_Group_ID", "Group_Label", "Option_ID",\n        "Option_Name", "Default", "Sort_Order",\n    ],\n    "Loadout_Weapons.csv": ["Loadout_Option_ID", "Weapon_ID", "Weapon_Role", "Sort_Order"],\n    "Loadout_Abilities.csv": ["Loadout_Option_ID", "Ability_ID", "Sort_Order"],\n    "Loadout_Points.csv": ["Loadout_Option_ID", "Point_Option_ID", "Label", "Cost", "Sort_Order"],\n    "Loadout_Compatibility.csv": [\n        "Loadout_Option_ID", "Required_Group_ID", "Compatible_Option_ID", "Rule_Order", "Option_Order",\n    ],\n    "Loadout_Legacy_Units.csv": ["Loadout_Option_ID", "Legacy_Unit_ID", "Sort_Order"],\n}\nCOMPAT = {\n    "Unit_Loadout_Options.csv": [\n        "Unit_ID", "Option_Group_ID", "Group_Label", "Option_ID", "Option_Name", "Default", "Sort_Order",\n    ],\n    "Unit_Loadout_Weapons.csv": [\n        "Unit_ID", "Option_Group_ID", "Option_ID", "Weapon_ID", "Weapon_Role", "Sort_Order",\n    ],\n    "Unit_Loadout_Abilities.csv": ["Unit_ID", "Option_Group_ID", "Option_ID", "Ability_ID", "Sort_Order"],\n    "Unit_Loadout_Points.csv": [\n        "Unit_ID", "Option_Group_ID", "Option_ID", "Point_Option_ID", "Label", "Cost", "Sort_Order",\n    ],\n    "Unit_Loadout_Compatibility.csv": [\n        "Unit_ID", "Option_Group_ID", "Option_ID", "Required_Group_ID",\n        "Compatible_Option_ID", "Rule_Order", "Option_Order",\n    ],\n    "Unit_Loadout_Legacy_Units.csv": [\n        "Unit_ID", "Option_Group_ID", "Option_ID", "Legacy_Unit_ID", "Sort_Order",\n    ],\n}\n\n\ndef fail(message):\n    raise SystemExit(message)\n\n\ndef read_dicts(path, expected_header=None):\n    with path.open(encoding="utf-8-sig", newline="") as handle:\n        reader = csv.DictReader(handle)\n        if expected_header is not None and reader.fieldnames != expected_header:\n            fail(\n                f"{path.relative_to(ROOT)} header mismatch\\n"\n                f"expected: {expected_header!r}\\nactual:   {reader.fieldnames!r}"\n            )\n        return [row for row in reader if any((value or "").strip() for value in row.values())]\n\n\ndef clean(value):\n    return (value or "").strip()\n\n\ndef split_ids(value):\n    return [part.strip() for part in (value or "").split(",") if part.strip()]\n\n\ndef actual_tuples(rows, columns):\n    return [tuple(clean(row.get(column)) for column in columns) for row in rows]\n\n\ndef legacy_expected(rows):\n    options = []\n    weapons = []\n    abilities = []\n    points = []\n    compatibility = []\n    legacy_units = []\n    for row in rows:\n        unit_id = clean(row.get("Unit_ID"))\n        group_id = clean(row.get("Option_Group_ID"))\n        option_id = clean(row.get("Option_ID"))\n        options.append((\n            unit_id, group_id, clean(row.get("Group_Label")), option_id,\n            clean(row.get("Option_Name")), clean(row.get("Default")), clean(row.get("Sort_Order")),\n        ))\n        for index, weapon_id in enumerate(split_ids(row.get("Weapon_IDs")), start=1):\n            weapons.append((unit_id, group_id, option_id, weapon_id, "SELECTED", str(index)))\n        for index, weapon_id in enumerate(split_ids(row.get("Preserve_Weapon_IDs")), start=1):\n            weapons.append((unit_id, group_id, option_id, weapon_id, "PRESERVE", str(index)))\n        for index, ability_id in enumerate(split_ids(row.get("Ability_IDs")), start=1):\n            abilities.append((unit_id, group_id, option_id, ability_id, str(index)))\n        for index in range(1, 3):\n            label = clean(row.get(f"Points_Label_{index}"))\n            cost = clean(row.get(f"Points_Cost_{index}"))\n            if label or cost:\n                points.append((unit_id, group_id, option_id, f"point_{index}", label, cost, str(index)))\n        for rule_order, raw_rule in enumerate((row.get("Compatible_With") or "").split(";"), start=1):\n            rule = raw_rule.strip()\n            if not rule:\n                continue\n            sep = "=" if "=" in rule else (":" if ":" in rule else None)\n            if not sep:\n                fail(f"invalid legacy compatibility rule {rule!r}")\n            required_group, option_text = rule.split(sep, 1)\n            for option_order, compatible_option in enumerate(\n                [part.strip() for part in option_text.split("|") if part.strip()], start=1\n            ):\n                compatibility.append((\n                    unit_id, group_id, option_id, required_group.strip(), compatible_option,\n                    str(rule_order), str(option_order),\n                ))\n        for index, legacy_unit_id in enumerate(split_ids(row.get("Legacy_Unit_IDs")), start=1):\n            legacy_units.append((unit_id, group_id, option_id, legacy_unit_id, str(index)))\n    return options, weapons, abilities, points, compatibility, legacy_units\n\n\ndef expected_compat_from_canonical(canonical):\n    options, weapons, abilities, points, compatibility, legacy_units = canonical\n    by_id = {clean(row["Loadout_Option_ID"]): row for row in options}\n\n    def parent(row):\n        p = by_id[clean(row["Loadout_Option_ID"])]\n        return p["Unit_ID"], p["Option_Group_ID"], p["Option_ID"]\n\n    return (\n        [\n            (\n                row["Unit_ID"], row["Option_Group_ID"], row["Group_Label"], row["Option_ID"],\n                row["Option_Name"], row["Default"], row["Sort_Order"],\n            )\n            for row in options\n        ],\n        [\n            (*parent(row), row["Weapon_ID"], row["Weapon_Role"], row["Sort_Order"])\n            for row in weapons\n        ],\n        [\n            (*parent(row), row["Ability_ID"], row["Sort_Order"])\n            for row in abilities\n        ],\n        [\n            (*parent(row), row["Point_Option_ID"], row["Label"], row["Cost"], row["Sort_Order"])\n            for row in points\n        ],\n        [\n            (*parent(row), row["Required_Group_ID"], row["Compatible_Option_ID"], row["Rule_Order"], row["Option_Order"])\n            for row in compatibility\n        ],\n        [\n            (*parent(row), row["Legacy_Unit_ID"], row["Sort_Order"])\n            for row in legacy_units\n        ],\n    )\n\n\ndef validate_army(army):\n    directory = ROOT / "data" / army\n    canonical = tuple(read_dicts(directory / filename, header) for filename, header in CANON.items())\n    compat_rows = tuple(read_dicts(directory / filename, header) for filename, header in COMPAT.items())\n    options, weapons, abilities, points, compatibility, legacy_units = canonical\n    compat_options, compat_weapons, compat_abilities, compat_points, compat_compatibility, compat_legacy_units = compat_rows\n\n    # Canonical IDs and semantic identity.\n    by_id = {}\n    semantic = set()\n    groups = defaultdict(set)\n    defaults = defaultdict(int)\n    for row in options:\n        lid = clean(row["Loadout_Option_ID"])\n        unit_id = clean(row["Unit_ID"])\n        group_id = clean(row["Option_Group_ID"])\n        option_id = clean(row["Option_ID"])\n        key = (unit_id, group_id, option_id)\n        if not lid:\n            fail(f"{army}: blank Loadout_Option_ID")\n        if lid in by_id:\n            fail(f"{army}: duplicate Loadout_Option_ID {lid!r}")\n        if key in semantic:\n            fail(f"{army}: duplicate semantic loadout option {key!r}")\n        by_id[lid] = row\n        semantic.add(key)\n        groups[(unit_id, group_id)].add(option_id)\n        if clean(row["Default"]).lower() in TRUE_VALUES:\n            defaults[(unit_id, group_id)] += 1\n    for group_key in groups:\n        if defaults[group_key] != 1:\n            fail(f"{army}: {group_key!r} must have exactly one default option")\n\n    for filename, rows in zip(list(CANON)[1:], canonical[1:]):\n        seen = set()\n        for row in rows:\n            lid = clean(row["Loadout_Option_ID"])\n            if lid not in by_id:\n                fail(f"{army}: {filename} references missing Loadout_Option_ID {lid!r}")\n            if filename in {"Loadout_Weapons.csv", "Loadout_Abilities.csv", "Loadout_Points.csv", "Loadout_Legacy_Units.csv"}:\n                natural = tuple(clean(row[c]) for c in CANON[filename])\n                if natural in seen:\n                    fail(f"{army}: duplicate row in {filename}: {natural!r}")\n                seen.add(natural)\n\n    # Canonical -> current Unit_Loadout_* compatibility must be exact.\n    expected_compat = expected_compat_from_canonical(canonical)\n    actual_compat = tuple(\n        actual_tuples(rows, header)\n        for rows, header in zip(compat_rows, COMPAT.values())\n    )\n    labels = ("options", "weapons", "abilities", "points", "compatibility", "legacy units")\n    for label, expected_rows, actual_rows in zip(labels, expected_compat, actual_compat):\n        if expected_rows != actual_rows:\n            fail(f"{army}: generated Unit_Loadout_* {label} do not exactly match canonical Loadout_* data")\n\n    # Current Unit_Weapon_Options compatibility must still expand to the current Unit_Loadout_* tables.\n    legacy = read_dicts(directory / "Unit_Weapon_Options.csv")\n    legacy_rows = legacy_expected(legacy)\n    for label, expected_rows, actual_rows in zip(labels, legacy_rows, actual_compat):\n        if expected_rows != actual_rows:\n            fail(f"{army}: Unit_Weapon_Options {label} do not exactly match generated Unit_Loadout_* data")\n\n    unit_ids = {clean(row.get("Unit_ID")) for row in read_dicts(directory / "Unit_Profiles.csv")}\n    weapon_ids = {clean(row.get("Weapon_ID")) for row in read_dicts(directory / "Weapon_Stats.csv")}\n    ability_ids = {clean(row.get("Ability_ID")) for row in read_dicts(directory / "Abilities.csv")}\n    universal_ability_ids = {\n        clean(row.get("Ability_ID"))\n        for row in read_dicts(ROOT / "data" / "universal" / "Universal_Abilities.csv")\n    }\n    all_ability_ids = ability_ids | universal_ability_ids\n\n    for lid, row in by_id.items():\n        if clean(row["Unit_ID"]) not in unit_ids:\n            fail(f"{army}: loadout {lid!r} references missing Unit_ID {row[\'Unit_ID\']!r}")\n\n    for row in weapons:\n        lid = clean(row["Loadout_Option_ID"])\n        weapon_id = clean(row["Weapon_ID"])\n        role = clean(row["Weapon_Role"])\n        if weapon_id not in weapon_ids:\n            fail(f"{army}: loadout {lid!r} references missing Weapon_ID {weapon_id!r}")\n        if role not in {"SELECTED", "PRESERVE"}:\n            fail(f"{army}: loadout {lid!r} has invalid Weapon_Role {role!r}")\n\n    for row in abilities:\n        lid = clean(row["Loadout_Option_ID"])\n        ability_id = clean(row["Ability_ID"])\n        if ability_id not in all_ability_ids:\n            fail(f"{army}: loadout {lid!r} references missing Ability_ID {ability_id!r}")\n\n    for row in compatibility:\n        lid = clean(row["Loadout_Option_ID"])\n        parent = by_id[lid]\n        required_group = clean(row["Required_Group_ID"])\n        compatible_option = clean(row["Compatible_Option_ID"])\n        if compatible_option not in groups.get((clean(parent["Unit_ID"]), required_group), set()):\n            fail(\n                f"{army}: compatibility for {lid!r} references unknown "\n                f"{required_group}/{compatible_option}"\n            )\n\n    print(\n        f"{army}: loadouts OK — {len(options)} Loadout_Option_IDs, {len(weapons)} weapons, "\n        f"{len(abilities)} abilities, {len(points)} points, {len(compatibility)} compatibility rows, "\n        f"{len(legacy_units)} legacy aliases"\n    )\n\n\ndef main():\n    for army in ARMIES:\n        validate_army(army)\n    print("canonical Loadout_Option_ID validation: OK")\n\n\nif __name__ == "__main__":\n    main()\n'
NEW_ENTITY_BLOCK = 'def derived_loadout_option_id(unit_id, group_id, option_id):\n    return f"{unit_id}__{group_id}__{option_id}"\n\n\ndef delete_unit_loadouts(state, army, unit_id):\n    options = state.t(army, "Loadout_Options.csv")\n    loadout_ids = {row["Loadout_Option_ID"] for row in options.rows if row.get("Unit_ID") == unit_id}\n    for filename in (\n        "Loadout_Weapons.csv", "Loadout_Abilities.csv", "Loadout_Points.csv",\n        "Loadout_Compatibility.csv", "Loadout_Legacy_Units.csv",\n    ):\n        state.t(army, filename).delete_where(lambda row, ids=loadout_ids: row.get("Loadout_Option_ID") in ids)\n    options.delete_where(lambda row, uid=unit_id: row.get("Unit_ID") == uid)\n\n\ndef delete_option_children(state, army, loadout_option_id, filenames=None):\n    targets = filenames or (\n        "Loadout_Weapons.csv", "Loadout_Abilities.csv", "Loadout_Points.csv",\n        "Loadout_Compatibility.csv", "Loadout_Legacy_Units.csv",\n    )\n    for filename in targets:\n        state.t(army, filename).delete_where(\n            lambda row, lid=loadout_option_id: row.get("Loadout_Option_ID") == lid\n        )\n\n\ndef set_default_exclusive(state, army, unit_id, group_id, loadout_option_id):\n    table = state.t(army, "Loadout_Options.csv")\n    for row in table.rows:\n        if row.get("Unit_ID") == unit_id and row.get("Option_Group_ID") == group_id:\n            row["Default"] = "TRUE" if row.get("Loadout_Option_ID") == loadout_option_id else "FALSE"\n\n\ndef add_loadout(state, army, data):\n    options = state.t(army, "Loadout_Options.csv")\n    unit_id = sval(data["Unit_ID"])\n    group_id = sval(data["Option_Group_ID"])\n    option_id = sval(data["Option_ID"])\n    loadout_option_id = sval(\n        data.get("Loadout_Option_ID") or derived_loadout_option_id(unit_id, group_id, option_id)\n    )\n    if options.exists(Loadout_Option_ID=loadout_option_id):\n        fail(f"Loadout_Option_ID already exists: {loadout_option_id!r}")\n    if options.exists(Unit_ID=unit_id, Option_Group_ID=group_id, Option_ID=option_id):\n        fail(f"semantic loadout option already exists: {unit_id}/{group_id}/{option_id}")\n    if not state.t(army, "Unit_Profiles.csv").exists(Unit_ID=unit_id):\n        fail(f"loadout references missing Unit_ID {unit_id!r}")\n    options.insert({\n        "Loadout_Option_ID": loadout_option_id,\n        "Unit_ID": unit_id,\n        "Option_Group_ID": group_id,\n        "Group_Label": data.get("Group_Label", ""),\n        "Option_ID": option_id,\n        "Option_Name": data["Option_Name"],\n        "Default": bool_csv(data["Default"]),\n        "Sort_Order": data["Sort_Order"],\n    })\n    if bool_csv(data["Default"]) == "TRUE":\n        set_default_exclusive(state, army, unit_id, group_id, loadout_option_id)\n    replace_loadout_children(state, army, loadout_option_id, data)\n\n\ndef replace_loadout_children(state, army, loadout_option_id, payload):\n    key = {"Loadout_Option_ID": loadout_option_id}\n    if "weapons" in payload:\n        delete_option_children(state, army, loadout_option_id, ("Loadout_Weapons.csv",))\n        table = state.t(army, "Loadout_Weapons.csv")\n        for index, item in enumerate(payload["weapons"], start=1):\n            table.insert({**key, "Weapon_ID": item["Weapon_ID"], "Weapon_Role": item.get("Weapon_Role", "SELECTED"), "Sort_Order": item.get("Sort_Order", index)})\n    if "abilities" in payload:\n        delete_option_children(state, army, loadout_option_id, ("Loadout_Abilities.csv",))\n        table = state.t(army, "Loadout_Abilities.csv")\n        for index, item in enumerate(payload["abilities"], start=1):\n            table.insert({**key, "Ability_ID": item["Ability_ID"], "Sort_Order": item.get("Sort_Order", index)})\n    if "points" in payload:\n        delete_option_children(state, army, loadout_option_id, ("Loadout_Points.csv",))\n        table = state.t(army, "Loadout_Points.csv")\n        for index, item in enumerate(payload["points"], start=1):\n            sort_order = item.get("Sort_Order", index)\n            table.insert({**key, "Point_Option_ID": item.get("Point_Option_ID") or f"point_{sort_order}", "Label": item.get("Label", ""), "Cost": item.get("Cost", ""), "Sort_Order": sort_order})\n    if "compatibility" in payload:\n        delete_option_children(state, army, loadout_option_id, ("Loadout_Compatibility.csv",))\n        table = state.t(army, "Loadout_Compatibility.csv")\n        for index, item in enumerate(payload["compatibility"], start=1):\n            table.insert({\n                **key,\n                "Required_Group_ID": item["Required_Group_ID"],\n                "Compatible_Option_ID": item["Compatible_Option_ID"],\n                "Rule_Order": item.get("Rule_Order", index),\n                "Option_Order": item.get("Option_Order", 1),\n            })\n    if "legacy_units" in payload:\n        delete_option_children(state, army, loadout_option_id, ("Loadout_Legacy_Units.csv",))\n        table = state.t(army, "Loadout_Legacy_Units.csv")\n        for index, item in enumerate(payload["legacy_units"], start=1):\n            table.insert({**key, "Legacy_Unit_ID": item["Legacy_Unit_ID"], "Sort_Order": item.get("Sort_Order", index)})\n'
OLD_LOADOUT_BRANCH = '    if entity == "loadout_option":\n        if mode == "add": add_loadout(state, army, data)\n        else:\n            key = option_key_from_id(entity_id)\n            table = state.t(army, "Loadout_Options.csv")\n            if mode == "change":\n                row = table.one(**key)\n                for key_name, col in {"Group_Label":"Group_Label","Option_Name":"Option_Name","Default":"Default","Sort_Order":"Sort_Order"}.items():\n                    if key_name in changes:\n                        row[col] = bool_csv(changes[key_name]) if key_name == "Default" else sval(changes[key_name])\n                if changes.get("Default") is True or str(changes.get("Default", "")).lower() in {"true","1","yes","y"}:\n                    set_default_exclusive(state, army, key["Unit_ID"], key["Option_Group_ID"], key["Option_ID"])\n                replace_loadout_children(state, army, key, changes)\n            else:\n                if table.delete_where(lambda r, k=key: all(r.get(c) == v for c, v in k.items())) != 1:\n                    fail(f"missing loadout option {key}")\n                delete_option_children(state, army, key)\n        return\n'
NEW_LOADOUT_BRANCH = '    if entity == "loadout_option":\n        if mode == "add":\n            add_loadout(state, army, data)\n        else:\n            loadout_option_id = sval(entity_id)\n            table = state.t(army, "Loadout_Options.csv")\n            if mode == "change":\n                row = table.one(Loadout_Option_ID=loadout_option_id)\n                for key_name, col in {"Group_Label":"Group_Label","Option_Name":"Option_Name","Default":"Default","Sort_Order":"Sort_Order"}.items():\n                    if key_name in changes:\n                        row[col] = bool_csv(changes[key_name]) if key_name == "Default" else sval(changes[key_name])\n                if changes.get("Default") is True or str(changes.get("Default", "")).lower() in {"true","1","yes","y"}:\n                    set_default_exclusive(state, army, row["Unit_ID"], row["Option_Group_ID"], loadout_option_id)\n                replace_loadout_children(state, army, loadout_option_id, changes)\n            else:\n                if table.delete_where(lambda r, lid=loadout_option_id: r.get("Loadout_Option_ID") == lid) != 1:\n                    fail(f"missing Loadout_Option_ID {loadout_option_id!r}")\n                delete_option_children(state, army, loadout_option_id)\n        return\n'
OLD_VALIDATE_BLOCK = '        option_keys = {(r["Unit_ID"], r["Option_Group_ID"], r["Option_ID"]) for r in options.rows}\n        for row in options.rows:\n            if row["Unit_ID"] not in unit_ids: fail(f"{army}: loadout missing Unit_ID {row[\'Unit_ID\']!r}")\n        child_specs = [\n            ("Loadout_Weapons.csv", "Weapon_ID", weapon_ids),\n            ("Loadout_Abilities.csv", "Ability_ID", ability_ids),\n            ("Loadout_Points.csv", None, None),\n            ("Loadout_Compatibility.csv", None, None),\n            ("Loadout_Legacy_Units.csv", None, None),\n        ]\n        for filename, ref_col, valid_ids in child_specs:\n            for row in state.t(army, filename).rows:\n                key = (row["Unit_ID"], row["Option_Group_ID"], row["Option_ID"])\n                if key not in option_keys: fail(f"{army}: {filename} references missing loadout option {key!r}")\n                if ref_col and row[ref_col] not in valid_ids: fail(f"{army}: {filename} missing {ref_col} {row[ref_col]!r}")\n'
NEW_VALIDATE_BLOCK = '        loadout_ids = {r["Loadout_Option_ID"] for r in options.rows}\n        group_options = {}\n        for row in options.rows:\n            if row["Unit_ID"] not in unit_ids:\n                fail(f"{army}: loadout missing Unit_ID {row[\'Unit_ID\']!r}")\n            group_options.setdefault((row["Unit_ID"], row["Option_Group_ID"]), set()).add(row["Option_ID"])\n        child_specs = [\n            ("Loadout_Weapons.csv", "Weapon_ID", weapon_ids),\n            ("Loadout_Abilities.csv", "Ability_ID", ability_ids),\n            ("Loadout_Points.csv", None, None),\n            ("Loadout_Compatibility.csv", None, None),\n            ("Loadout_Legacy_Units.csv", None, None),\n        ]\n        for filename, ref_col, valid_ids in child_specs:\n            for row in state.t(army, filename).rows:\n                lid = row["Loadout_Option_ID"]\n                if lid not in loadout_ids:\n                    fail(f"{army}: {filename} references missing Loadout_Option_ID {lid!r}")\n                if ref_col and row[ref_col] not in valid_ids:\n                    fail(f"{army}: {filename} missing {ref_col} {row[ref_col]!r}")\n        option_by_id = {r["Loadout_Option_ID"]: r for r in options.rows}\n        for row in state.t(army, "Loadout_Compatibility.csv").rows:\n            parent = option_by_id[row["Loadout_Option_ID"]]\n            target = group_options.get((parent["Unit_ID"], row["Required_Group_ID"]), set())\n            if row["Compatible_Option_ID"] not in target:\n                fail(\n                    f"{army}: compatibility for {row[\'Loadout_Option_ID\']!r} references "\n                    f"unknown {row[\'Required_Group_ID\']}/{row[\'Compatible_Option_ID\']}"\n                )\n'


def fail(message):
    raise SystemExit(message)


def read_rows(path, header):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != header:
            fail(f"{path.relative_to(ROOT)} header mismatch: {reader.fieldnames!r}")
        return [dict(row) for row in reader if any((v or "").strip() for v in row.values())]


def write_rows(path, header, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def clean(value):
    return (value or "").strip()


def make_loadout_id(unit_id, group_id, option_id):
    return f"{unit_id}__{group_id}__{option_id}"


def migrate_army(army):
    base = ROOT / "data" / army
    old = {name: read_rows(base / name, header) for name, header in OLD_HEADERS.items()}
    by_key = {}
    by_id = {}
    new_options = []
    for row in old["Unit_Loadout_Options.csv"]:
        key = (clean(row["Unit_ID"]), clean(row["Option_Group_ID"]), clean(row["Option_ID"]))
        if key in by_key:
            fail(f"{army}: duplicate current loadout key {key!r}")
        lid = make_loadout_id(*key)
        if lid in by_id:
            fail(f"{army}: generated Loadout_Option_ID collision {lid!r}")
        by_key[key] = lid
        by_id[lid] = key
        new_options.append({
            "Loadout_Option_ID": lid,
            "Unit_ID": row["Unit_ID"],
            "Option_Group_ID": row["Option_Group_ID"],
            "Group_Label": row["Group_Label"],
            "Option_ID": row["Option_ID"],
            "Option_Name": row["Option_Name"],
            "Default": row["Default"],
            "Sort_Order": row["Sort_Order"],
        })

    def lid_for(row):
        key = (clean(row["Unit_ID"]), clean(row["Option_Group_ID"]), clean(row["Option_ID"]))
        if key not in by_key:
            fail(f"{army}: child row references missing loadout option {key!r}")
        return by_key[key]

    new_tables = {
        "Loadout_Options.csv": new_options,
        "Loadout_Weapons.csv": [
            {"Loadout_Option_ID": lid_for(r), "Weapon_ID": r["Weapon_ID"], "Weapon_Role": r["Weapon_Role"], "Sort_Order": r["Sort_Order"]}
            for r in old["Unit_Loadout_Weapons.csv"]
        ],
        "Loadout_Abilities.csv": [
            {"Loadout_Option_ID": lid_for(r), "Ability_ID": r["Ability_ID"], "Sort_Order": r["Sort_Order"]}
            for r in old["Unit_Loadout_Abilities.csv"]
        ],
        "Loadout_Points.csv": [
            {"Loadout_Option_ID": lid_for(r), "Point_Option_ID": r["Point_Option_ID"], "Label": r["Label"], "Cost": r["Cost"], "Sort_Order": r["Sort_Order"]}
            for r in old["Unit_Loadout_Points.csv"]
        ],
        "Loadout_Compatibility.csv": [
            {"Loadout_Option_ID": lid_for(r), "Required_Group_ID": r["Required_Group_ID"], "Compatible_Option_ID": r["Compatible_Option_ID"], "Rule_Order": r["Rule_Order"], "Option_Order": r["Option_Order"]}
            for r in old["Unit_Loadout_Compatibility.csv"]
        ],
        "Loadout_Legacy_Units.csv": [
            {"Loadout_Option_ID": lid_for(r), "Legacy_Unit_ID": r["Legacy_Unit_ID"], "Sort_Order": r["Sort_Order"]}
            for r in old["Unit_Loadout_Legacy_Units.csv"]
        ],
    }
    for filename, rows in new_tables.items():
        write_rows(base / filename, NEW_HEADERS[filename], rows)
    print(
        f"{army}: {len(new_options)} Loadout_Option_IDs created "
        f"({len(new_tables['Loadout_Weapons.csv'])} weapon links, "
        f"{len(new_tables['Loadout_Abilities.csv'])} ability links, "
        f"{len(new_tables['Loadout_Points.csv'])} point rows, "
        f"{len(new_tables['Loadout_Compatibility.csv'])} compatibility rows, "
        f"{len(new_tables['Loadout_Legacy_Units.csv'])} legacy aliases)"
    )


def rewrite_schema():
    path = ROOT / "data" / "CSV_SCHEMA.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        header = reader.fieldnames
        rows = list(reader)
    if header != ["Scope","File","Column_Order","Column_Name","Required","Ownership","Notes"]:
        fail("CSV_SCHEMA.csv unexpected header")

    rows = [row for row in rows if row["File"] not in set(OLD_HEADERS) and row["File"] not in NEW_HEADERS]

    notes = {
        "Loadout_Options.csv": [
            "Stable unique loadout option key.",
            "Foreign key to Unit_Profiles.csv.",
            "Stable option-group key within a unit.",
            "Visible option-group label.",
            "Stable semantic option key within the unit/group.",
            "Visible loadout option name.",
            "Exactly one default option per unit/group.",
            "Display order within the option group.",
        ],
        "Loadout_Weapons.csv": [
            "Foreign key to Loadout_Options.csv.",
            "Foreign key to Weapon_Stats.csv.",
            "SELECTED adds/replaces the option weapons; PRESERVE retains a base weapon.",
            "Order within the selected or preserved weapon list.",
        ],
        "Loadout_Abilities.csv": [
            "Foreign key to Loadout_Options.csv.",
            "Ability granted by selecting this loadout option.",
            "Order within the option ability list.",
        ],
        "Loadout_Points.csv": [
            "Foreign key to Loadout_Options.csv.",
            "Stable option-specific point slot key.",
            "Option-specific unit-size label; blank is valid.",
            "Option-specific point cost; blank is valid for loadout-driven behavior.",
            "Point-option display order.",
        ],
        "Loadout_Compatibility.csv": [
            "Foreign key to Loadout_Options.csv.",
            "Other option group constrained by this rule.",
            "Allowed option in Required_Group_ID; multiple rows are OR alternatives.",
            "Original compatibility rule order.",
            "Original allowed-option order within the rule.",
        ],
        "Loadout_Legacy_Units.csv": [
            "Foreign key to Loadout_Options.csv.",
            "Historical unit ID migrated to this selected option.",
            "Original alias order.",
        ],
    }
    req = {
        "Loadout_Options.csv": [1,1,1,0,1,1,1,1],
        "Loadout_Weapons.csv": [1,1,1,1],
        "Loadout_Abilities.csv": [1,1,1],
        "Loadout_Points.csv": [1,1,0,0,1],
        "Loadout_Compatibility.csv": [1,1,1,1,1],
        "Loadout_Legacy_Units.csv": [1,1,1],
    }

    new_rows = []
    for filename, columns in NEW_HEADERS.items():
        for idx, col in enumerate(columns, start=1):
            new_rows.append({
                "Scope":"army","File":filename,"Column_Order":str(idx),"Column_Name":col,
                "Required":"YES" if req[filename][idx-1] else "NO",
                "Ownership":"AUTHORITATIVE","Notes":notes[filename][idx-1],
            })

    compat_rows = []
    for filename, columns in OLD_HEADERS.items():
        canonical = filename.replace("Unit_", "", 1)
        for idx, col in enumerate(columns, start=1):
            compat_rows.append({
                "Scope":"army","File":filename,"Column_Order":str(idx),"Column_Name":col,
                "Required":"NO" if (
                    (filename == "Unit_Loadout_Options.csv" and col == "Group_Label") or
                    (filename == "Unit_Loadout_Points.csv" and col in {"Label", "Cost"})
                ) else "YES",
                "Ownership":"GENERATED_COMPAT",
                "Notes":f"Generated from canonical {canonical} using Loadout_Option_ID; retained for current HTML compatibility.",
            })

    insert_at = next((i for i, row in enumerate(rows) if row["File"] == "Effects.csv"), len(rows))
    rows[insert_at:insert_at] = new_rows + compat_rows

    for row in rows:
        if row["File"] == "Unit_Weapon_Options.csv":
            row["Notes"] = (row["Notes"] or "").replace(
                "normalized Unit_Loadout_* tables",
                "canonical Loadout_* tables via generated Unit_Loadout_* compatibility tables",
            )

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print("CSV_SCHEMA.csv: canonical Loadout_* authoritative; Unit_Loadout_* generated compatibility")


def rewrite_entity_schema():
    path = ROOT / "schemas" / "entity-ops.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    defs = schema["$defs"]
    id_prop = {"type":"string","minLength":1}
    defs["loadoutAdd"]["properties"]["Loadout_Option_ID"] = id_prop
    defs["nestedLoadoutAdd"]["properties"]["Loadout_Option_ID"] = id_prop
    defs["loadoutId"] = id_prop
    path.write_text(json.dumps(schema, separators=(",", ":")) + "\n", encoding="utf-8")
    print("entity-ops.schema.json: loadout CHANGE/DELETE now takes one Loadout_Option_ID")


def rewrite_entity_ops():
    path = ROOT / "scripts" / "entity_ops.py"
    text = path.read_text(encoding="utf-8")

    header_replacements = {
        '"Unit_Loadout_Options.csv": ["Unit_ID", "Option_Group_ID", "Group_Label", "Option_ID", "Option_Name", "Default", "Sort_Order"],':
        '"Loadout_Options.csv": ["Loadout_Option_ID", "Unit_ID", "Option_Group_ID", "Group_Label", "Option_ID", "Option_Name", "Default", "Sort_Order"],',
        '"Unit_Loadout_Weapons.csv": ["Unit_ID", "Option_Group_ID", "Option_ID", "Weapon_ID", "Weapon_Role", "Sort_Order"],':
        '"Loadout_Weapons.csv": ["Loadout_Option_ID", "Weapon_ID", "Weapon_Role", "Sort_Order"],',
        '"Unit_Loadout_Abilities.csv": ["Unit_ID", "Option_Group_ID", "Option_ID", "Ability_ID", "Sort_Order"],':
        '"Loadout_Abilities.csv": ["Loadout_Option_ID", "Ability_ID", "Sort_Order"],',
        '"Unit_Loadout_Points.csv": ["Unit_ID", "Option_Group_ID", "Option_ID", "Point_Option_ID", "Label", "Cost", "Sort_Order"],':
        '"Loadout_Points.csv": ["Loadout_Option_ID", "Point_Option_ID", "Label", "Cost", "Sort_Order"],',
        '"Unit_Loadout_Compatibility.csv": ["Unit_ID", "Option_Group_ID", "Option_ID", "Required_Group_ID", "Compatible_Option_ID", "Rule_Order", "Option_Order"],':
        '"Loadout_Compatibility.csv": ["Loadout_Option_ID", "Required_Group_ID", "Compatible_Option_ID", "Rule_Order", "Option_Order"],',
        '"Unit_Loadout_Legacy_Units.csv": ["Unit_ID", "Option_Group_ID", "Option_ID", "Legacy_Unit_ID", "Sort_Order"],':
        '"Loadout_Legacy_Units.csv": ["Loadout_Option_ID", "Legacy_Unit_ID", "Sort_Order"],',
    }
    for old, new in header_replacements.items():
        if old not in text:
            fail(f"entity_ops.py missing expected header pattern: {old}")
        text = text.replace(old, new)

    for old, new in (
        ("Unit_Loadout_Options.csv","Loadout_Options.csv"),
        ("Unit_Loadout_Weapons.csv","Loadout_Weapons.csv"),
        ("Unit_Loadout_Abilities.csv","Loadout_Abilities.csv"),
        ("Unit_Loadout_Points.csv","Loadout_Points.csv"),
        ("Unit_Loadout_Compatibility.csv","Loadout_Compatibility.csv"),
        ("Unit_Loadout_Legacy_Units.csv","Loadout_Legacy_Units.csv"),
    ):
        text = text.replace(old, new)

    start = text.index("def option_key_from_id(value):")
    end = text.index("\ndef add_unit(state, army, data):", start)
    text = text[:start] + NEW_ENTITY_BLOCK + text[end:]

    if OLD_LOADOUT_BRANCH not in text:
        fail("entity_ops.py loadout operation branch pattern missing")
    text = text.replace(OLD_LOADOUT_BRANCH, NEW_LOADOUT_BRANCH)

    old_unique = 'unique(options, ["Unit_ID", "Option_Group_ID", "Option_ID"], f"{army} loadout option")'
    if old_unique not in text:
        fail("entity_ops.py loadout unique pattern missing")
    text = text.replace(
        old_unique,
        'unique(options, ["Loadout_Option_ID"], f"{army} Loadout_Option_ID")\n        '
        'unique(options, ["Unit_ID", "Option_Group_ID", "Option_ID"], f"{army} semantic loadout option")'
    )

    if OLD_VALIDATE_BLOCK not in text:
        fail("entity_ops.py loadout validation pattern missing")
    text = text.replace(OLD_VALIDATE_BLOCK, NEW_VALIDATE_BLOCK)

    path.write_text(text, encoding="utf-8")
    print("entity_ops.py: loadout CRUD now uses canonical Loadout_Option_ID")


def install_permanent_scripts():
    (ROOT / "scripts" / "split_loadouts_v1.py").write_text(SPLIT_LOADOUTS, encoding="utf-8")
    (ROOT / "scripts" / "validate_loadouts.py").write_text(VALIDATE_LOADOUTS, encoding="utf-8")
    print("permanent loadout generator and validator installed")


def main():
    for army in ARMIES:
        migrate_army(army)
    rewrite_schema()
    rewrite_entity_schema()
    rewrite_entity_ops()
    install_permanent_scripts()
    print("Loadout_Option_ID migration preparation: OK")


if __name__ == "__main__":
    main()
