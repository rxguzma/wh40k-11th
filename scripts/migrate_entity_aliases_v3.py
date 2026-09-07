#!/usr/bin/env python3
import re
from collections import defaultdict
from pathlib import Path

import migrate_entity_aliases_v1 as migration
import migrate_entity_aliases_v2 as runner

ROOT = Path(__file__).resolve().parents[1]
ARMIES = ("marines", "orks", "nids")
NEW_MARKER = re.compile(r"(?:^NEW(?:_|$)|_NEW(?:_|$)|\(New\))", re.IGNORECASE)


def canonicalize_new_id(value):
    text = value or ""
    text = re.sub(r"\(\s*New\s*\)", "", text, flags=re.IGNORECASE)
    previous = None
    while previous != text:
        previous = text
        text = re.sub(r"^NEW_", "", text, flags=re.IGNORECASE)
        text = re.sub(r"_NEW$", "", text, flags=re.IGNORECASE)
        text = re.sub(r"_NEW_", "_", text, flags=re.IGNORECASE)
    text = re.sub(r"[^A-Za-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_").upper()
    if not text:
        migration.fail(f"cannot canonicalize empty ID from {value!r}")
    return text


def clean_name(value):
    return re.sub(r"\s*\(\s*New\s*\)\s*$", "", value or "", flags=re.IGNORECASE).strip()


def migrate_simple_entity_table(path, id_col, name_col, entity_type, army, aliases):
    rows, header = migration.read_dicts(path)
    source_rows = {row[id_col]: row for row in rows}
    new_sources = [row[id_col] for row in rows if NEW_MARKER.search(row[id_col])]
    mapping = {source: canonicalize_new_id(source) for source in new_sources}
    if not mapping:
        return {}, set()

    groups = defaultdict(set)
    for source, target in mapping.items():
        groups[target].add(source)
        if target in source_rows:
            groups[target].add(target)

    canonical_rows = {}
    for target, members in groups.items():
        preferred = next((member for member in members if member in mapping), None)
        if not preferred:
            migration.fail(f"{path.relative_to(ROOT)}: no New source for target {target}")
        row = dict(source_rows[preferred])
        row[id_col] = target
        if name_col and name_col in row:
            row[name_col] = clean_name(row[name_col])
        canonical_rows[target] = row
        for member in sorted(members):
            if member != target:
                migration.add_alias(aliases, entity_type, army, member, target)

    member_to_target = {}
    for target, members in groups.items():
        for member in members:
            member_to_target[member] = target

    emitted = set()
    rebuilt = []
    for row in rows:
        row_id = row[id_col]
        target = member_to_target.get(row_id)
        if target:
            if target not in emitted:
                rebuilt.append(canonical_rows[target])
                emitted.add(target)
            continue
        rebuilt.append(row)
    migration.write_dicts(path, header, rebuilt)
    print(f"{path.relative_to(ROOT)}: {len(mapping)} New IDs -> {len(groups)} canonical IDs")
    collisions = {target for target, members in groups.items() if target in source_rows and any(m != target for m in members)}
    return mapping, collisions


def replace_column(path, column, mapping):
    if not mapping:
        return 0
    rows, header = migration.read_dicts(path)
    changed = 0
    for row in rows:
        old = row[column]
        new = mapping.get(old, old)
        if new != old:
            row[column] = new
            changed += 1
    migration.write_dicts(path, header, rows)
    return changed


def migrate_army_abilities(army, aliases):
    base = ROOT / "data" / army
    mapping, _ = migrate_simple_entity_table(
        base / "Abilities.csv", "Ability_ID", "Ability Name", "ability", army, aliases
    )
    if not mapping:
        return
    a = replace_column(base / "Unit_Abilities.csv", "Ability_ID", mapping)
    b = replace_column(base / "Loadout_Abilities.csv", "Ability_ID", mapping)
    effects, header = migration.read_dicts(base / "Effects.csv")
    c = 0
    for row in effects:
        if row.get("Source_Type") == "ABILITY" and row.get("Source_ID") in mapping:
            row["Source_ID"] = mapping[row["Source_ID"]]
            c += 1
    migration.write_dicts(base / "Effects.csv", header, effects)
    print(f"{army}: rewrote {a+b+c} ability references")


def migrate_weapon_ability_rows(base, mapping, source_weapon_ids_before):
    path = base / "Weapon_Abilities.csv"
    rows, header = migration.read_dicts(path)
    by_weapon = defaultdict(list)
    for row in rows:
        by_weapon[row["Weapon_ID"]].append(row)

    target_to_source = {}
    for source, target in mapping.items():
        target_to_source[target] = source

    affected = set(mapping) | set(mapping.values())
    rebuilt = [row for row in rows if row["Weapon_ID"] not in affected]
    for target, source in target_to_source.items():
        for index, source_row in enumerate(by_weapon.get(source, []), start=1):
            row = dict(source_row)
            row["Weapon_ID"] = target
            suffix = source_row["Weapon_Ability_ID"].split(":", 1)[1] if ":" in source_row["Weapon_Ability_ID"] else f"ability_{index}"
            row["Weapon_Ability_ID"] = f"{target}:{suffix}"
            rebuilt.append(row)
    migration.write_dicts(path, header, rebuilt)
    print(f"{path.relative_to(ROOT)}: rebuilt abilities for {len(mapping)} renamed weapons")


def migrate_army_weapons(army, aliases):
    base = ROOT / "data" / army
    before, _ = migration.read_dicts(base / "Weapon_Stats.csv")
    before_ids = {row["Weapon_ID"] for row in before}
    mapping, _ = migrate_simple_entity_table(
        base / "Weapon_Stats.csv", "Weapon_ID", "Weapon Name", "weapon", army, aliases
    )
    if not mapping:
        return
    a = replace_column(base / "Unit_Weapons.csv", "Weapon_ID", mapping)
    b = replace_column(base / "Loadout_Weapons.csv", "Weapon_ID", mapping)
    migrate_weapon_ability_rows(base, mapping, before_ids)
    print(f"{army}: rewrote {a+b} weapon references")


def migrate_universal_stratagems(aliases):
    path = ROOT / "data" / "universal" / "Universal_Stratagems.csv"
    migrate_simple_entity_table(
        path, "Item_ID", "Item_Name", "universal_stratagem", "universal", aliases
    )


def main():
    aliases = []
    migration.migrate_universal_abilities(aliases)
    migration.migrate_units(aliases)
    migration.replace_universal_ability_references()

    for army in ARMIES:
        migrate_army_abilities(army, aliases)
        migrate_army_weapons(army, aliases)
    migrate_universal_stratagems(aliases)

    migration.write_alias_file(aliases)
    migration.patch_csv_schema()
    migration.write_alias_validator()
    runner.write_no_new_validator()
    runner.ensure_entity_ops_re_import()
    migration.patch_entity_ops()
    migration.patch_json_schema()
    print("entity alias migration v3: OK")


if __name__ == "__main__":
    main()
