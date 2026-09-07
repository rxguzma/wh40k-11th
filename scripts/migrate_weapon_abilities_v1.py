#!/usr/bin/env python3
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMIES = ("marines", "orks", "nids")
WEAPON_STATS_HEADER = ["Weapon_ID", "Weapon Name", 'R"', "A", "WS", "St", "AP", "D", "Weapon Abilities"]
WEAPON_ABILITIES_HEADER = ["Weapon_ID", "Weapon_Ability_ID", "Ability_Type", "Target", "Value", "Condition", "Separator_Before", "Sort_Order"]
PARAMETERIZED = ("SUSTAINED HITS", "RAPID FIRE", "MELTA", "BLAST", "CLEAVE", "DEADLY DEMISE")


def fail(message):
    raise SystemExit(message)


def read_dict_rows(path, expected_header):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != expected_header:
            fail(f"{path.relative_to(ROOT)} header mismatch: {reader.fieldnames!r}")
        return [row for row in reader if any((value or "").strip() for value in row.values())]


def write_dict_rows(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parse_token(token):
    token = token.strip()
    if token == "-":
        return {"Ability_Type": "NONE", "Target": "", "Value": "", "Condition": ""}

    condition = ""
    body = token
    if ":" in token:
        body, condition = token.split(":", 1)
        body = body.strip()
        condition = condition.strip()

    anti = re.fullmatch(r"ANTI-(\S+)\s+(\S+)", body)
    if anti:
        return {
            "Ability_Type": "ANTI",
            "Target": anti.group(1),
            "Value": anti.group(2),
            "Condition": condition,
        }

    for ability_type in PARAMETERIZED:
        prefix = ability_type + " "
        if body.startswith(prefix):
            return {
                "Ability_Type": ability_type,
                "Target": "",
                "Value": body[len(prefix):].strip(),
                "Condition": condition,
            }

    return {"Ability_Type": body, "Target": "", "Value": "", "Condition": condition}


def render(parsed):
    ability_type = parsed["Ability_Type"]
    if ability_type == "NONE":
        text = "-"
    elif ability_type == "ANTI":
        text = f"ANTI-{parsed['Target']} {parsed['Value']}"
    else:
        text = ability_type
        if parsed.get("Value"):
            text += f" {parsed['Value']}"
    if parsed.get("Condition"):
        text += f": {parsed['Condition']}"
    return text


def split_with_separators(raw):
    parts = re.split(r"(,\s*)", raw)
    if not parts or not parts[0].strip():
        fail(f"invalid Weapon Abilities string {raw!r}")
    result = [("", parts[0].strip())]
    index = 1
    while index < len(parts):
        separator = parts[index]
        if index + 1 >= len(parts) or not parts[index + 1].strip():
            fail(f"invalid Weapon Abilities separator structure {raw!r}")
        result.append((separator, parts[index + 1].strip()))
        index += 2
    return result


def render_rows(rows):
    output = ""
    for row in sorted(rows, key=lambda item: int(item["Sort_Order"])):
        output += (row.get("Separator_Before") or "") + render(row)
    return output


def migrate_data():
    for army in ARMIES:
        directory = ROOT / "data" / army
        stats = read_dict_rows(directory / "Weapon_Stats.csv", WEAPON_STATS_HEADER)
        target = directory / "Weapon_Abilities.csv"
        if target.exists():
            rows = read_dict_rows(target, WEAPON_ABILITIES_HEADER)
            grouped = {}
            for row in rows:
                grouped.setdefault(row["Weapon_ID"], []).append(row)
            for stat in stats:
                rendered = render_rows(grouped.get(stat["Weapon_ID"], []))
                if rendered != (stat.get("Weapon Abilities") or ""):
                    fail(f"{army}: existing Weapon_Abilities.csv does not round-trip {stat['Weapon_ID']!r}")
            print(f"{army}: Weapon_Abilities.csv already current ({len(rows)} rows)")
            continue

        rows = []
        for stat in stats:
            weapon_id = (stat.get("Weapon_ID") or "").strip()
            raw = stat.get("Weapon Abilities") or ""
            if not raw:
                continue
            normalized = []
            for index, (separator, token) in enumerate(split_with_separators(raw), start=1):
                parsed = parse_token(token)
                row = {
                    "Weapon_ID": weapon_id,
                    "Weapon_Ability_ID": f"{weapon_id}:ability_{index}",
                    "Ability_Type": parsed["Ability_Type"],
                    "Target": parsed["Target"],
                    "Value": parsed["Value"],
                    "Condition": parsed["Condition"],
                    "Separator_Before": separator,
                    "Sort_Order": str(index),
                }
                normalized.append(row)
                rows.append(row)
            round_trip = render_rows(normalized)
            if round_trip != raw:
                fail(
                    f"{army}: Weapon Abilities round-trip mismatch for {weapon_id!r}\n"
                    f"source: {raw!r}\nrender: {round_trip!r}"
                )
        write_dict_rows(target, WEAPON_ABILITIES_HEADER, rows)
        print(f"{army}: created Weapon_Abilities.csv ({len(rows)} normalized rows)")


def migrate_csv_schema():
    path = ROOT / "data" / "CSV_SCHEMA.csv"
    header = ["Scope", "File", "Column_Order", "Column_Name", "Required", "Ownership", "Notes"]
    rows = read_dict_rows(path, header)

    for row in rows:
        if row["Scope"] == "army" and row["File"] == "Weapon_Stats.csv" and row["Column_Name"] == "Weapon Abilities":
            row["Ownership"] = "GENERATED_COLUMN"
            row["Notes"] = "Generated from authoritative Weapon_Abilities.csv; compatibility/presentation column for current HTML."

    existing = [row for row in rows if row["Scope"] == "army" and row["File"] == "Weapon_Abilities.csv"]
    if not existing:
        new_rows = [
            ["Weapon_ID", "YES", "Foreign key to Weapon_Stats.csv."],
            ["Weapon_Ability_ID", "YES", "Stable unique relationship key generated from Weapon_ID and ability order."],
            ["Ability_Type", "YES", "Canonical weapon ability type; NONE preserves an explicit legacy '-' value."],
            ["Target", "NO", "Target class for parameterized abilities such as ANTI; blank otherwise."],
            ["Value", "NO", "Structured parameter such as 2, D3, or 4+; blank for flag abilities."],
            ["Condition", "NO", "Optional qualifier previously represented after ':' in the compatibility string."],
            ["Separator_Before", "NO", "Exact legacy delimiter before this ability; blank for first ability, normally ', ' thereafter."],
            ["Sort_Order", "YES", "Ability display/order position within the weapon."],
        ]
        insert_at = max(i for i, row in enumerate(rows) if row["File"] == "Weapon_Stats.csv") + 1
        payload = []
        for order, (column, required, notes) in enumerate(new_rows, start=1):
            payload.append({
                "Scope": "army",
                "File": "Weapon_Abilities.csv",
                "Column_Order": str(order),
                "Column_Name": column,
                "Required": required,
                "Ownership": "AUTHORITATIVE",
                "Notes": notes,
            })
        rows[insert_at:insert_at] = payload
        print("CSV_SCHEMA.csv: added authoritative Weapon_Abilities.csv schema")
    else:
        columns = [row["Column_Name"] for row in sorted(existing, key=lambda row: int(row["Column_Order"]))]
        if columns != WEAPON_ABILITIES_HEADER:
            fail(f"existing Weapon_Abilities.csv schema differs from expected: {columns!r}")
        print("CSV_SCHEMA.csv: Weapon_Abilities schema already present")

    write_dict_rows(path, header, rows)


def patch_entity_schema():
    path = ROOT / "schemas" / "entity-ops.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    defs = schema["$defs"]
    defs["weaponAbility"] = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "Ability_Type": {"type": "string", "minLength": 1},
            "Target": {"type": "string"},
            "Value": {"type": ["string", "number", "integer"]},
            "Condition": {"type": "string"},
            "Sort_Order": {"type": "integer", "minimum": 1},
        },
        "required": ["Ability_Type"],
    }
    for name in ("weaponAdd", "weaponChange"):
        props = defs[name]["properties"]
        props.pop("Weapon_Abilities", None)
        props["weapon_abilities"] = {"type": "array", "items": {"$ref": "#/$defs/weaponAbility"}}
    path.write_text(json.dumps(schema, separators=(",", ":")) + "\n", encoding="utf-8")
    print("entity-ops.schema.json: weapon_abilities is now structured")


def patch_entity_ops():
    path = ROOT / "scripts" / "entity_ops.py"
    text = path.read_text(encoding="utf-8")
    if '"Weapon_Abilities.csv": [' not in text:
        needle = '    "Weapon_Stats.csv": ["Weapon_ID", "Weapon Name", \'R"\', "A", "WS", "St", "AP", "D", "Weapon Abilities"],\n'
        insert = needle + '    "Weapon_Abilities.csv": ["Weapon_ID", "Weapon_Ability_ID", "Ability_Type", "Target", "Value", "Condition", "Separator_Before", "Sort_Order"],\n'
        if needle not in text:
            fail("cannot patch entity_ops HEADERS")
        text = text.replace(needle, insert, 1)

    old_files = '                "Weapon_Stats.csv", "Abilities.csv", "Detachment_Definitions.csv", "Enhancements.csv",\n'
    new_files = '                "Weapon_Stats.csv", "Weapon_Abilities.csv", "Abilities.csv", "Detachment_Definitions.csv", "Enhancements.csv",\n'
    if old_files in text:
        text = text.replace(old_files, new_files, 1)

    text = text.replace('        "St": "St", "AP": "AP", "D": "D", "Weapon_Abilities": "Weapon Abilities",\n', '        "St": "St", "AP": "AP", "D": "D",\n', 1)

    if "def replace_weapon_abilities(" not in text:
        marker = "def replace_effects(state, army, source_type, source_id, effects):\n"
        helper = '''def replace_weapon_abilities(state, army, weapon_id, abilities):\n    table = state.t(army, "Weapon_Abilities.csv")\n    table.delete_where(lambda row: row.get("Weapon_ID") == weapon_id)\n    for index, ability in enumerate(abilities, start=1):\n        sort_order = ability.get("Sort_Order", index)\n        table.insert({\n            "Weapon_ID": weapon_id,\n            "Weapon_Ability_ID": f"{weapon_id}:ability_{index}",\n            "Ability_Type": ability["Ability_Type"],\n            "Target": ability.get("Target", ""),\n            "Value": ability.get("Value", ""),\n            "Condition": ability.get("Condition", ""),\n            "Separator_Before": "" if index == 1 else ", ",\n            "Sort_Order": sort_order,\n        })\n\n\n'''
        if marker not in text:
            fail("cannot insert replace_weapon_abilities helper")
        text = text.replace(marker, helper + marker, 1)

    start = text.find('    if entity == "weapon":\n')
    end = text.find('    if entity == "ability":\n', start)
    if start < 0 or end < 0:
        fail("cannot locate weapon entity block")
    weapon_block = '''    if entity == "weapon":\n        table = state.t(army, "Weapon_Stats.csv")\n        if mode == "add":\n            wid = sval(data["Weapon_ID"])\n            add_simple(table, "Weapon_ID", weapon_row(data), "Weapon_ID")\n            if "weapon_abilities" in data:\n                replace_weapon_abilities(state, army, wid, data["weapon_abilities"])\n        elif mode == "change":\n            wid = sval(entity_id)\n            row = table.one(Weapon_ID=wid)\n            row.update(weapon_row(changes, row))\n            if "weapon_abilities" in changes:\n                replace_weapon_abilities(state, army, wid, changes["weapon_abilities"])\n        else:\n            wid = sval(entity_id)\n            delete_simple(table, "Weapon_ID", wid, "Weapon_ID")\n            state.t(army, "Weapon_Abilities.csv").delete_where(lambda r: r.get("Weapon_ID") == wid)\n            state.t(army, "Unit_Weapons.csv").delete_where(lambda r: r.get("Weapon_ID") == wid)\n            state.t(army, "Unit_Loadout_Weapons.csv").delete_where(lambda r: r.get("Weapon_ID") == wid)\n        return\n\n'''
    text = text[:start] + weapon_block + text[end:]

    if 'weapon_abilities = state.t(army, "Weapon_Abilities.csv")' not in text:
        needle = '        weapons = state.t(army, "Weapon_Stats.csv")\n'
        if needle not in text:
            fail("cannot add weapon_abilities validation table")
        text = text.replace(needle, needle + '        weapon_abilities = state.t(army, "Weapon_Abilities.csv")\n', 1)

    if 'f"{army} Weapon_Ability_ID"' not in text:
        needle = '        unique(weapons, ["Weapon_ID"], f"{army} Weapon_ID")\n'
        insert = needle + '        unique(weapon_abilities, ["Weapon_Ability_ID"], f"{army} Weapon_Ability_ID")\n        unique(weapon_abilities, ["Weapon_ID", "Sort_Order"], f"{army} weapon ability sort order")\n'
        if needle not in text:
            fail("cannot add weapon ability uniqueness validation")
        text = text.replace(needle, insert, 1)

    if 'Weapon_Abilities missing Weapon_ID' not in text:
        needle = '        ability_ids = idset(abilities, "Ability_ID") | universal_abilities\n'
        insert = needle + '''        for row in weapon_abilities.rows:\n            if row["Weapon_ID"] not in weapon_ids:\n                fail(f"{army}: Weapon_Abilities missing Weapon_ID {row['Weapon_ID']!r}")\n            if not (row.get("Ability_Type") or "").strip():\n                fail(f"{army}: Weapon_Abilities blank Ability_Type for {row['Weapon_Ability_ID']!r}")\n            if row["Ability_Type"] == "ANTI" and (not row["Target"] or not row["Value"]):\n                fail(f"{army}: ANTI weapon ability requires Target and Value for {row['Weapon_Ability_ID']!r}")\n\n'''
        if needle not in text:
            fail("cannot add weapon ability reference validation")
        text = text.replace(needle, insert, 1)

    path.write_text(text, encoding="utf-8")
    print("entity_ops.py: weapon operations now author Weapon_Abilities.csv")


def patch_workflows():
    data_path = ROOT / ".github" / "workflows" / "data-schema.yml"
    text = data_path.read_text(encoding="utf-8")
    if "scripts/split_weapon_abilities_v1.py" not in text:
        text = text.replace("      - 'scripts/split_units_v1.py'\n", "      - 'scripts/split_units_v1.py'\n      - 'scripts/split_weapon_abilities_v1.py'\n")
    if "scripts/validate_weapon_abilities.py" not in text:
        text = text.replace("      - 'scripts/validate_unit_relations.py'\n", "      - 'scripts/validate_unit_relations.py'\n      - 'scripts/validate_weapon_abilities.py'\n")
    if "Sync weapon ability compatibility column" not in text:
        marker = "      - name: Sync legacy loadout compatibility table\n"
        step = "      - name: Sync weapon ability compatibility column\n        run: python3 scripts/split_weapon_abilities_v1.py\n\n"
        if marker not in text:
            fail("cannot add weapon ability sync to Data Schema workflow")
        text = text.replace(marker, step + marker, 1)
    if "Validate normalized weapon abilities" not in text:
        marker = "      - name: Validate normalized loadouts\n"
        step = "      - name: Validate normalized weapon abilities\n        run: python3 scripts/validate_weapon_abilities.py\n\n"
        if marker not in text:
            fail("cannot add weapon ability validation to Data Schema workflow")
        text = text.replace(marker, step + marker, 1)
    data_path.write_text(text, encoding="utf-8")

    entity_path = ROOT / ".github" / "workflows" / "entity-ops.yml"
    text = entity_path.read_text(encoding="utf-8")
    if "python3 scripts/split_weapon_abilities_v1.py" not in text:
        text = text.replace("          python3 scripts/split_units_v1.py\n", "          python3 scripts/split_units_v1.py\n          python3 scripts/split_weapon_abilities_v1.py\n", 1)
    if "python3 scripts/validate_weapon_abilities.py" not in text:
        text = text.replace("          python3 scripts/validate_unit_relations.py\n", "          python3 scripts/validate_unit_relations.py\n          python3 scripts/validate_weapon_abilities.py\n", 1)
    entity_path.write_text(text, encoding="utf-8")
    print("workflows: weapon ability generation and validation added")


def main():
    migrate_data()
    migrate_csv_schema()
    patch_entity_schema()
    patch_entity_ops()
    patch_workflows()
    print("weapon ability normalization migration: OK")


if __name__ == "__main__":
    main()
