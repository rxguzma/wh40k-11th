#!/usr/bin/env python3
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMIES = ("marines", "orks", "nids")

UNIVERSAL_ABILITY_ALIASES = {
    "ANTI (New)": "ANTI",
    "CLEAVE (New)": "CLEAVE",
    "CLOSE-QUARTERS (New)": "CLOSE_QUARTERS",
    "CLOSE-QUARTERS": "CLOSE_QUARTERS",
    "DEADLY DEMISE (New)": "DEADLY_DEMISE",
    "DEEP STRIKE (New)": "DEEP_STRIKE",
    "DEVASTATING WOUNDS (New)": "DEVASTATING_WOUNDS",
    "DEVASTATING WOUNDS": "DEVASTATING_WOUNDS",
    "EXTRA ATTACKS (New)": "EXTRA_ATTACKS",
    "EXTRA ATTACKS": "EXTRA_ATTACKS",
    "FEEL NO PAIN (New)": "FEEL_NO_PAIN",
    "FIGHTS FIRST (New)": "FIGHTS_FIRST",
    "HAZARDOUS (New)": "HAZARDOUS",
    "HEAVY (New)": "HEAVY",
    "HOVER (New)": "HOVER",
    "IGNORES COVER (New)": "IGNORES_COVER",
    "IGNORES COVER": "IGNORES_COVER",
    "INDIRECT FIRE (New)": "INDIRECT_FIRE",
    "INDIRECT FIRE": "INDIRECT_FIRE",
    "INFILTRATORS (New)": "INFILTRATORS",
    "LANCE (New)": "LANCE",
    "LEADER (New)": "LEADER",
    "LETHAL HITS (New)": "LETHAL_HITS",
    "LETHAL HITS": "LETHAL_HITS",
    "LONE_OPERATIVE_NEW": "LONE_OPERATIVE",
    "PISTOL_NEW": "PISTOL",
    "PRECISION_NEW": "PRECISION",
    "PSYCHIC_NEW": "PSYCHIC",
    "RAPID_FIRE_NEW": "RAPID_FIRE",
    "STEALTH_NEW": "STEALTH",
    "SUPER_HEAVY_WALKER_NEW": "SUPER_HEAVY_WALKER",
    "SUPPORT_NEW": "SUPPORT",
    "SUSTAINED_HITS_NEW": "SUSTAINED_HITS",
    "TORRENT_NEW": "TORRENT",
    "TWIN_LINKED_NEW": "TWIN_LINKED",
}

UNIT_ALIASES = {
    "marines": {
        "NEW_ANCIENT": "ANCIENT",
        "NEW_CHAPLAIN_WITH_JUMP_PACK": "CHAPLAIN_WITH_JUMP_PACK",
    },
    "orks": {},
    "nids": {},
}

ALIAS_HEADER = ["Entity_Type", "Army", "Alias_ID", "Canonical_ID", "Status"]
UNIVERSAL_ABILITY_HEADER = ["Ability_ID", "Ability Name", "Short Description", "Long Description", "Order"]
CANONICAL_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
NEW_ID_RE = re.compile(r"(?:^NEW(?:_|$)|_NEW(?:_|$)|\(New\))", re.IGNORECASE)
NEW_NAME_RE = re.compile(r"\(\s*New\s*\)", re.IGNORECASE)


def fail(message):
    raise SystemExit(message)


def read_dicts(path, expected=None):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if expected is not None and reader.fieldnames != expected:
            fail(f"{path.relative_to(ROOT)} header mismatch: {reader.fieldnames!r} != {expected!r}")
        return list(reader), list(reader.fieldnames or [])


def write_dicts(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def is_new_variant(value):
    return bool(NEW_ID_RE.search(value or ""))


def clean_display_name(value):
    return NEW_NAME_RE.sub("", value or "").strip()


def canonical_loadout_id(row):
    return f"{row['Unit_ID']}__{row['Option_Group_ID']}__{row['Option_ID']}"


def add_alias(alias_rows, entity_type, army, alias_id, canonical_id):
    if alias_id == canonical_id:
        return
    alias_rows.append({
        "Entity_Type": entity_type,
        "Army": army,
        "Alias_ID": alias_id,
        "Canonical_ID": canonical_id,
        "Status": "DEPRECATED",
    })


def migrate_universal_abilities(alias_rows):
    path = ROOT / "data" / "universal" / "Universal_Abilities.csv"
    rows, _ = read_dicts(path, UNIVERSAL_ABILITY_HEADER)
    by_id = {row["Ability_ID"]: row for row in rows}

    grouped = defaultdict(list)
    for alias_id, target in UNIVERSAL_ABILITY_ALIASES.items():
        if alias_id in by_id:
            grouped[target].append(alias_id)
    missing_new = [source for source in UNIVERSAL_ABILITY_ALIASES if is_new_variant(source) and source not in by_id]
    if missing_new:
        fail(f"expected universal New variants are missing: {missing_new}")

    canonical_rows = {}
    members_by_target = {}
    for target, aliases in grouped.items():
        members = set(aliases)
        if target in by_id:
            members.add(target)
        preferred = [alias for alias in aliases if is_new_variant(alias)]
        source_id = preferred[0] if preferred else (target if target in by_id else aliases[0])
        source = dict(by_id[source_id])
        source["Ability_ID"] = target
        source["Ability Name"] = clean_display_name(source["Ability Name"])
        canonical_rows[target] = source
        members_by_target[target] = members
        for alias_id in sorted(members):
            if alias_id != target:
                add_alias(alias_rows, "universal_ability", "universal", alias_id, target)

    emitted = set()
    rebuilt = []
    id_to_target = {}
    for target, members in members_by_target.items():
        for member in members:
            id_to_target[member] = target
    for row in rows:
        row_id = row["Ability_ID"]
        target = id_to_target.get(row_id)
        if target:
            if target not in emitted:
                rebuilt.append(canonical_rows[target])
                emitted.add(target)
            continue
        rebuilt.append(row)

    write_dicts(path, UNIVERSAL_ABILITY_HEADER, rebuilt)
    print(f"universal abilities: {len(rows)} -> {len(rebuilt)} rows; {len(canonical_rows)} canonicalized groups")


def migrate_units(alias_rows):
    for army in ARMIES:
        mapping = UNIT_ALIASES[army]
        if not mapping:
            continue
        base = ROOT / "data" / army
        profiles_path = base / "Unit_Profiles.csv"
        profiles, header = read_dicts(profiles_path)
        ids = {row["Unit_ID"] for row in profiles}
        missing = [old for old in mapping if old not in ids]
        collisions = [new for new in mapping.values() if new in ids]
        if missing:
            fail(f"{army}: expected New unit IDs missing: {missing}")
        if collisions:
            fail(f"{army}: canonical unit ID collision: {collisions}")
        for row in profiles:
            old = row["Unit_ID"]
            if old in mapping:
                row["Unit_ID"] = mapping[old]
                add_alias(alias_rows, "unit", army, old, mapping[old])
        write_dicts(profiles_path, header, profiles)

        for filename in ("Unit_Abilities.csv", "Unit_Weapons.csv", "Unit_Points.csv"):
            path = base / filename
            rows, child_header = read_dicts(path)
            for row in rows:
                row["Unit_ID"] = mapping.get(row["Unit_ID"], row["Unit_ID"])
            write_dicts(path, child_header, rows)

        options_path = base / "Loadout_Options.csv"
        options, options_header = read_dicts(options_path)
        loadout_aliases = {}
        for row in options:
            old_loadout_id = row["Loadout_Option_ID"]
            row["Unit_ID"] = mapping.get(row["Unit_ID"], row["Unit_ID"])
            new_loadout_id = canonical_loadout_id(row)
            if old_loadout_id != new_loadout_id:
                loadout_aliases[old_loadout_id] = new_loadout_id
                row["Loadout_Option_ID"] = new_loadout_id
                add_alias(alias_rows, "loadout_option", army, old_loadout_id, new_loadout_id)
        write_dicts(options_path, options_header, options)

        if loadout_aliases:
            for filename in (
                "Loadout_Weapons.csv", "Loadout_Abilities.csv", "Loadout_Points.csv",
                "Loadout_Compatibility.csv", "Loadout_Legacy_Units.csv",
            ):
                path = base / filename
                rows, child_header = read_dicts(path)
                for row in rows:
                    row["Loadout_Option_ID"] = loadout_aliases.get(row["Loadout_Option_ID"], row["Loadout_Option_ID"])
                write_dicts(path, child_header, rows)
        print(f"{army}: renamed {len(mapping)} unit IDs; {len(loadout_aliases)} loadout IDs followed unit renames")


def replace_universal_ability_references():
    for army in ARMIES:
        base = ROOT / "data" / army
        for filename in ("Unit_Abilities.csv", "Loadout_Abilities.csv"):
            path = base / filename
            rows, header = read_dicts(path)
            changed = 0
            for row in rows:
                old = row["Ability_ID"]
                new = UNIVERSAL_ABILITY_ALIASES.get(old, old)
                if new != old:
                    row["Ability_ID"] = new
                    changed += 1
            write_dicts(path, header, rows)
            print(f"{army}/{filename}: canonicalized {changed} universal ability references")


def write_alias_file(alias_rows):
    path = ROOT / "data" / "universal" / "Entity_Aliases.csv"
    unique = {}
    for row in alias_rows:
        key = (row["Entity_Type"], row["Army"], row["Alias_ID"])
        if key in unique and unique[key]["Canonical_ID"] != row["Canonical_ID"]:
            fail(f"conflicting alias mapping for {key}: {unique[key]} vs {row}")
        unique[key] = row
    rows = sorted(unique.values(), key=lambda r: (r["Entity_Type"], r["Army"], r["Alias_ID"]))
    write_dicts(path, ALIAS_HEADER, rows)
    print(f"Entity_Aliases.csv: {len(rows)} deprecated aliases")


def patch_csv_schema():
    path = ROOT / "data" / "CSV_SCHEMA.csv"
    rows, header = read_dicts(path)
    rows = [row for row in rows if not (row["Scope"] == "universal" and row["File"] == "Entity_Aliases.csv")]
    notes = {
        "Entity_Type": "Entity type resolved by this alias.",
        "Army": "Owning army slug, or universal for universal entities.",
        "Alias_ID": "Deprecated historical ID accepted only for compatibility; may preserve legacy naming.",
        "Canonical_ID": "Current canonical entity ID.",
        "Status": "Alias lifecycle status; currently DEPRECATED.",
    }
    for index, column in enumerate(ALIAS_HEADER, start=1):
        rows.append({
            "Scope": "universal", "File": "Entity_Aliases.csv", "Column_Order": str(index),
            "Column_Name": column, "Required": "YES", "Ownership": "AUTHORITATIVE", "Notes": notes[column],
        })
    write_dicts(path, header, rows)
    print("CSV_SCHEMA.csv: registered Entity_Aliases.csv")


def write_alias_validator():
    path = ROOT / "scripts" / "validate_aliases.py"
    content = r'''#!/usr/bin/env python3
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMIES = ("marines", "orks", "nids")
HEADER = ["Entity_Type", "Army", "Alias_ID", "Canonical_ID", "Status"]
NEW_ID_RE = re.compile(r"(?:^NEW(?:_|$)|_NEW(?:_|$)|\(New\))", re.IGNORECASE)
TARGETS = {
    "unit": ("army", "Unit_Profiles.csv", "Unit_ID"),
    "weapon": ("army", "Weapon_Stats.csv", "Weapon_ID"),
    "ability": ("army", "Abilities.csv", "Ability_ID"),
    "detachment": ("army", "Detachment_Definitions.csv", "Detachment_ID"),
    "enhancement": ("army", "Enhancements.csv", "Enhancement_ID"),
    "stratagem": ("army", "Stratagems.csv", "Stratagem_ID"),
    "army_rule": ("army", "Army_Rules.csv", "Army_Rule_ID"),
    "effect": ("army", "Effects.csv", "Effect_ID"),
    "loadout_option": ("army", "Loadout_Options.csv", "Loadout_Option_ID"),
    "universal_ability": ("universal", "Universal_Abilities.csv", "Ability_ID"),
    "universal_stratagem": ("universal", "Universal_Stratagems.csv", "Item_ID"),
}


def fail(message):
    raise SystemExit(message)


def ids(path, column):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return {(row.get(column) or "").strip() for row in reader if (row.get(column) or "").strip()}


def main():
    path = ROOT / "data" / "universal" / "Entity_Aliases.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != HEADER:
            fail(f"Entity_Aliases.csv header mismatch: {reader.fieldnames!r}")
        rows = list(reader)
    seen = {}
    alias_keys = set()
    for line_no, row in enumerate(rows, start=2):
        entity = (row.get("Entity_Type") or "").strip()
        army = (row.get("Army") or "").strip()
        alias_id = (row.get("Alias_ID") or "").strip()
        canonical_id = (row.get("Canonical_ID") or "").strip()
        status = (row.get("Status") or "").strip()
        if entity not in TARGETS:
            fail(f"line {line_no}: unsupported Entity_Type {entity!r}")
        scope, filename, id_col = TARGETS[entity]
        if scope == "universal" and army != "universal":
            fail(f"line {line_no}: {entity} requires Army=universal")
        if scope == "army" and army not in ARMIES:
            fail(f"line {line_no}: {entity} requires an army slug")
        if not alias_id or not canonical_id or alias_id == canonical_id:
            fail(f"line {line_no}: invalid alias identity")
        if status != "DEPRECATED":
            fail(f"line {line_no}: Status must be DEPRECATED")
        if NEW_ID_RE.search(canonical_id):
            fail(f"line {line_no}: canonical ID still contains New marker: {canonical_id!r}")
        key = (entity, army, alias_id)
        if key in seen:
            fail(f"duplicate alias {key!r}: lines {seen[key]} and {line_no}")
        seen[key] = line_no
        alias_keys.add(key)
        target_path = ROOT / "data" / ("universal" if scope == "universal" else army) / filename
        if canonical_id not in ids(target_path, id_col):
            fail(f"line {line_no}: missing canonical target {canonical_id!r} in {target_path.relative_to(ROOT)}")
    for row in rows:
        key = (row["Entity_Type"], row["Army"], row["Canonical_ID"])
        if key in alias_keys:
            fail(f"alias chain is not allowed: {row['Alias_ID']!r} -> {row['Canonical_ID']!r}")
    print(f"entity aliases OK — {len(rows)} deprecated aliases")


if __name__ == "__main__":
    main()
'''
    path.write_text(content, encoding="utf-8")
    print("validate_aliases.py: created")


def patch_entity_ops():
    path = ROOT / "scripts" / "entity_ops.py"
    text = path.read_text(encoding="utf-8")
    if '"Entity_Aliases.csv"' not in text:
        old = '    "Universal_Abilities.csv": ["Ability_ID", "Ability Name", "Short Description", "Long Description", "Order"],\n'
        new = old + '    "Entity_Aliases.csv": ["Entity_Type", "Army", "Alias_ID", "Canonical_ID", "Status"],\n'
        if old not in text:
            fail("entity_ops.py Universal_Abilities header anchor not found")
        text = text.replace(old, new, 1)

    old = '        self.tables[(UNIVERSAL, "Universal_Abilities.csv")] = Table(base / "Universal_Abilities.csv", HEADERS["Universal_Abilities.csv"])\n'
    new = old + '        self.tables[(UNIVERSAL, "Entity_Aliases.csv")] = Table(base / "Entity_Aliases.csv", HEADERS["Entity_Aliases.csv"])\n'
    if 'self.tables[(UNIVERSAL, "Entity_Aliases.csv")]' not in text:
        if old not in text:
            fail("entity_ops.py universal State anchor not found")
        text = text.replace(old, new, 1)

    marker = '\ndef schema_validate(payload):\n'
    if 'def resolve_entity_alias(' not in text:
        helper = r'''

def resolve_entity_alias(state, entity_type, army, value):
    raw = sval(value)
    matches = state.t(UNIVERSAL, "Entity_Aliases.csv").find(
        Entity_Type=entity_type, Army=army, Alias_ID=raw
    )
    if not matches:
        return raw
    if len(matches) != 1:
        fail(f"ambiguous entity alias {entity_type}/{army}/{raw!r}")
    return matches[0]["Canonical_ID"]


def validate_new_entity_id(value, label):
    text = sval(value)
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*", text):
        fail(f"{label} must use UPPER_SNAKE_CASE: {text!r}")
    if re.search(r"(?:^NEW(?:_|$)|_NEW(?:_|$))", text):
        fail(f"{label} must not contain NEW: {text!r}")


def validate_new_display_names(value, path="data"):
    if isinstance(value, dict):
        for key, item in value.items():
            validate_new_display_names(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            validate_new_display_names(item, f"{path}[{index}]")
    elif isinstance(value, str) and re.search(r"\(\s*New\s*\)", value, re.IGNORECASE):
        fail(f"{path} must not contain '(New)': {value!r}")


PRIMARY_ADD_IDS = {
    "unit": ("Unit_ID",),
    "weapon": ("Weapon_ID",),
    "ability": ("Ability_ID",),
    "detachment": ("Detachment_ID", "Rule_ID"),
    "enhancement": ("Enhancement_ID",),
    "stratagem": ("Stratagem_ID",),
    "army_rule": ("Army_Rule_ID",),
    "universal_ability": ("Ability_ID",),
    "universal_stratagem": ("Item_ID",),
}
'''
        if marker not in text:
            fail("entity_ops.py schema_validate marker not found")
        text = text.replace(marker, helper + marker, 1)

    old = '    entity_id = op.get("id")\n    print(f"op {index}: {mode} {entity} [{army}]")\n'
    new = '''    entity_id = op.get("id")\n    if mode == "add":\n        validate_new_display_names(data)\n        for field in PRIMARY_ADD_IDS.get(entity, ()):\n            if field in data:\n                validate_new_entity_id(data[field], field)\n        if entity == "detachment":\n            for enhancement in data.get("enhancements", []):\n                validate_new_entity_id(enhancement["Enhancement_ID"], "Enhancement_ID")\n            for stratagem in data.get("stratagems", []):\n                validate_new_entity_id(stratagem["Stratagem_ID"], "Stratagem_ID")\n    if mode != "add" and isinstance(entity_id, str):\n        entity_id = resolve_entity_alias(state, entity, army, entity_id)\n    print(f"op {index}: {mode} {entity} [{army}]")\n'''
    if 'validate_new_display_names(data)' not in text:
        if old not in text:
            fail("entity_ops.py apply_operation anchor not found")
        text = text.replace(old, new, 1)

    path.write_text(text, encoding="utf-8")
    print("entity_ops.py: alias resolution + canonical ADD ID rules installed")


def patch_json_schema():
    path = ROOT / "schemas" / "entity-ops.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    defs = schema["$defs"]
    defs["canonicalId"] = {
        "type": "string",
        "pattern": "^(?!NEW(?:_|$))(?!.*_NEW(?:_|$))[A-Z][A-Z0-9_]*$",
    }
    targets = {
        "unitAdd": ["Unit_ID"],
        "weaponAdd": ["Weapon_ID"],
        "abilityAdd": ["Ability_ID"],
        "detachmentAdd": ["Detachment_ID", "Rule_ID"],
        "enhancementAdd": ["Enhancement_ID"],
        "nestedEnhancementAdd": ["Enhancement_ID"],
        "stratagemAdd": ["Stratagem_ID"],
        "nestedStratagemAdd": ["Stratagem_ID"],
        "armyRuleAdd": ["Army_Rule_ID"],
        "universalAbilityAdd": ["Ability_ID"],
        "universalStratagemAdd": ["Item_ID"],
    }
    for def_name, fields in targets.items():
        for field in fields:
            defs[def_name]["properties"][field] = {"$ref": "#/$defs/canonicalId"}
    for def_name in ("loadoutAdd", "nestedLoadoutAdd"):
        if "Loadout_Option_ID" in defs[def_name]["properties"]:
            defs[def_name]["properties"]["Loadout_Option_ID"] = {"$ref": "#/$defs/canonicalId"}
    path.write_text(json.dumps(schema, separators=(",", ":")) + "\n", encoding="utf-8")
    print("entity-ops.schema.json: canonical ADD IDs enforced")


def audit_no_visible_new():
    issues = []
    for path in sorted((ROOT / "data").rglob("*.csv")):
        if path.name == "Entity_Aliases.csv":
            continue
        rows, header = read_dicts(path)
        for line_no, row in enumerate(rows, start=2):
            for column, value in row.items():
                if not value:
                    continue
                is_id = column == "Item_ID" or column.endswith("_ID") or column in {"Ability_ID", "Weapon_ID", "Unit_ID"}
                is_name = column.endswith("Name") or column.endswith("_Name") or column in {"Ability Name", "Weapon Name", "Unit Name"}
                if column in {"Legacy_Unit_ID"}:
                    continue
                if is_id and NEW_ID_RE.search(value):
                    issues.append(f"{path.relative_to(ROOT)}:{line_no}:{column}={value}")
                if is_name and NEW_NAME_RE.search(value):
                    issues.append(f"{path.relative_to(ROOT)}:{line_no}:{column}={value}")
    if issues:
        fail("remaining New identifiers/names outside hidden aliases:\n" + "\n".join(issues))
    print("visible/canonical New-name audit: OK")


def main():
    alias_rows = []
    migrate_universal_abilities(alias_rows)
    migrate_units(alias_rows)
    replace_universal_ability_references()
    write_alias_file(alias_rows)
    patch_csv_schema()
    write_alias_validator()
    patch_entity_ops()
    patch_json_schema()
    audit_no_visible_new()
    print("entity alias migration: OK")


if __name__ == "__main__":
    main()
