#!/usr/bin/env python3
import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "entity-ops.schema.json"
ARMIES = ("marines", "orks", "nids")
UNIVERSAL = "universal"

HEADERS = {
    "Unit_Profiles.csv": ["Unit_ID", "Unit Name", 'M"', "T", "SV", "W", "LD", "OC", "Keywords", "Hyperlink"],
    "Unit_Abilities.csv": ["Unit_ID", "Ability_ID", "Ability_Type"],
    "Unit_Weapons.csv": ["Unit_ID", "Weapon_ID"],
    "Unit_Points.csv": ["Unit_ID", "Point_Option_ID", "Label", "Cost", "Sort_Order"],
    "Weapon_Stats.csv": ["Weapon_ID", "Weapon Name", 'R"', "A", "WS", "St", "AP", "D", "Weapon Abilities"],
    "Weapon_Abilities.csv": ["Weapon_ID", "Weapon_Ability_ID", "Ability_Type", "Target", "Value", "Condition", "Separator_Before", "Sort_Order"],
    "Abilities.csv": ["Ability_ID", "Ability Name", "Short_Description", "Long_Description", "Tags", "Tag Categories", "Order", "Default_Active"],
    "Detachment_Definitions.csv": ["Detachment_ID", "Army_Name", "Detachment_Name", "Rule_ID", "Rule_Name", "DP_Cost", "Detachment_Disposition", "Detachment_Disposition_2", "Short_Description", "Long_Description"],
    "Enhancements.csv": ["Enhancement_ID", "Detachment_ID", "Enhancement_Name", "Points", "Repeatable", "Short_Description", "Long_Description", "Tags"],
    "Stratagems.csv": ["Stratagem_ID", "Detachment_ID", "Stratagem_Name", "CP_Cost", "Short_Description", "Long_Description"],
    "Army_Rules.csv": ["Army_Rule_ID", "Army_Name", "Rule_Name", "Short_Description", "Long_Description"],
    "Effects.csv": ["Effect_ID", "Source_Type", "Source_ID", "Effect_Type", "Target", "Stat", "Operation", "Value", "Display_Tag", "Sort_Order"],
    "Loadout_Options.csv": ["Loadout_Option_ID", "Unit_ID", "Option_Group_ID", "Group_Label", "Option_ID", "Option_Name", "Default", "Sort_Order"],
    "Loadout_Weapons.csv": ["Loadout_Option_ID", "Weapon_ID", "Weapon_Role", "Sort_Order"],
    "Loadout_Abilities.csv": ["Loadout_Option_ID", "Ability_ID", "Sort_Order"],
    "Loadout_Points.csv": ["Loadout_Option_ID", "Point_Option_ID", "Label", "Cost", "Sort_Order"],
    "Loadout_Compatibility.csv": ["Loadout_Option_ID", "Required_Group_ID", "Compatible_Option_ID", "Rule_Order", "Option_Order"],
    "Universal_Abilities.csv": ["Ability_ID", "Ability Name", "Short_Description", "Long_Description", "Order"],
    "Universal_Stratagems.csv": ["Detachment_ID", "Detachment_Name", "Item_Type", "Item_ID", "Item_Name", "Points", "CP_Cost", "Short_Description", "Long_Description"],
}

ENTITY_TYPES = {
    "unit", "weapon", "ability", "detachment", "enhancement", "stratagem",
    "army_rule", "effect", "loadout_option", "universal_ability", "universal_stratagem",
}


def fail(message):
    raise SystemExit(message)


def sval(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    return str(value)


def bool_csv(value):
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return "TRUE"
    if text in {"false", "0", "no", "n"}:
        return "FALSE"
    fail(f"invalid boolean value {value!r}")


class Table:
    def __init__(self, path, header):
        self.path = path
        self.header = header
        if not path.is_file():
            fail(f"missing canonical CSV: {path.relative_to(ROOT)}")
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != header:
                fail(
                    f"header mismatch in {path.relative_to(ROOT)}\n"
                    f"expected: {header!r}\nactual:   {reader.fieldnames!r}"
                )
            self.rows = [dict(row) for row in reader if any((v or "").strip() for v in row.values())]
        self.original = [dict(row) for row in self.rows]

    def write(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.header, lineterminator="\n")
            writer.writeheader()
            writer.writerows(self.rows)

    @property
    def changed(self):
        return self.rows != self.original

    def find(self, **keys):
        return [row for row in self.rows if all((row.get(k) or "") == sval(v) for k, v in keys.items())]

    def one(self, **keys):
        matches = self.find(**keys)
        if len(matches) != 1:
            fail(f"{self.path.relative_to(ROOT)} expected 1 row for {keys}, found {len(matches)}")
        return matches[0]

    def exists(self, **keys):
        return bool(self.find(**keys))

    def insert(self, row, top=False):
        unknown = set(row) - set(self.header)
        if unknown:
            fail(f"unknown columns for {self.path.relative_to(ROOT)}: {sorted(unknown)}")
        normalized = {col: sval(row.get(col, "")) for col in self.header}
        if top:
            self.rows.insert(0, normalized)
        else:
            self.rows.append(normalized)
        return normalized

    def delete_where(self, predicate):
        before = len(self.rows)
        self.rows = [row for row in self.rows if not predicate(row)]
        return before - len(self.rows)


class State:
    def __init__(self):
        self.tables = {}
        for army in ARMIES:
            base = ROOT / "data" / army
            for filename in (
                "Unit_Profiles.csv", "Unit_Abilities.csv", "Unit_Weapons.csv", "Unit_Points.csv",
                "Weapon_Stats.csv", "Weapon_Abilities.csv", "Abilities.csv", "Detachment_Definitions.csv", "Enhancements.csv",
                "Stratagems.csv", "Army_Rules.csv", "Effects.csv", "Loadout_Options.csv",
                "Loadout_Weapons.csv", "Loadout_Abilities.csv", "Loadout_Points.csv",
                "Loadout_Compatibility.csv",
            ):
                self.tables[(army, filename)] = Table(base / filename, HEADERS[filename])
        base = ROOT / "data" / UNIVERSAL
        self.tables[(UNIVERSAL, "Universal_Abilities.csv")] = Table(base / "Universal_Abilities.csv", HEADERS["Universal_Abilities.csv"])
        self.tables[(UNIVERSAL, "Universal_Stratagems.csv")] = Table(base / "Universal_Stratagems.csv", HEADERS["Universal_Stratagems.csv"])

    def t(self, army, filename):
        return self.tables[(army, filename)]

    def write_changed(self):
        changed = []
        for table in self.tables.values():
            if table.changed:
                table.write()
                changed.append(str(table.path.relative_to(ROOT)))
        return changed

    def army_name(self, army):
        rows = self.t(army, "Detachment_Definitions.csv").rows
        for row in rows:
            if (row.get("Army_Name") or "").strip():
                return row["Army_Name"]
        fallback = {"marines": "Space Marines", "orks": "Orks", "nids": "Tyranids"}
        return fallback[army]



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

def schema_validate(payload):
    try:
        import jsonschema
    except ImportError:
        fail("jsonschema package is required; workflow must install it")
    if not SCHEMA_PATH.is_file():
        fail(f"missing JSON schema: {SCHEMA_PATH.relative_to(ROOT)}")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    try:
        jsonschema.Draft202012Validator(schema).validate(payload)
    except jsonschema.ValidationError as exc:
        path = ".".join(str(part) for part in exc.absolute_path)
        prefix = f" at {path}" if path else ""
        fail(f"entity ops schema validation failed{prefix}: {exc.message}")


def ensure_entity_army(entity_type, army):
    if entity_type.startswith("universal_"):
        if army != UNIVERSAL:
            fail(f"{entity_type} requires army='universal'")
    elif army not in ARMIES:
        fail(f"{entity_type} requires army in {ARMIES}")


def unique(table, columns, label):
    seen = set()
    for row in table.rows:
        key = tuple((row.get(col) or "").strip() for col in columns)
        if key in seen:
            fail(f"duplicate {label}: {key!r}")
        seen.add(key)


def idset(table, column):
    return {(row.get(column) or "").strip() for row in table.rows if (row.get(column) or "").strip()}


def all_ability_ids(state, army):
    return idset(state.t(army, "Abilities.csv"), "Ability_ID") | idset(state.t(UNIVERSAL, "Universal_Abilities.csv"), "Ability_ID")


def profile_row(data, existing=None):
    row = dict(existing or {col: "" for col in HEADERS["Unit_Profiles.csv"]})
    mapping = {
        "Unit_ID": "Unit_ID", "Unit_Name": "Unit Name", "M": 'M"', "T": "T", "SV": "SV",
        "W": "W", "LD": "LD", "OC": "OC", "Keywords": "Keywords", "Hyperlink": "Hyperlink",
    }
    for key, col in mapping.items():
        if key in data:
            row[col] = sval(data[key])
    return row


def weapon_row(data, existing=None):
    row = dict(existing or {col: "" for col in HEADERS["Weapon_Stats.csv"]})
    mapping = {
        "Weapon_ID": "Weapon_ID", "Weapon_Name": "Weapon Name", "R": 'R"', "A": "A", "WS": "WS",
        "St": "St", "AP": "AP", "D": "D",
    }
    for key, col in mapping.items():
        if key in data:
            row[col] = sval(data[key])
    return row


def ability_row(data, existing=None):
    row = dict(existing or {col: "" for col in HEADERS["Abilities.csv"]})
    mapping = {
        "Ability_ID": "Ability_ID", "Ability_Name": "Ability Name", "Short_Description": "Short_Description",
        "Long_Description": "Long_Description", "Order": "Order",
    }
    for key, col in mapping.items():
        if key in data:
            row[col] = sval(data[key])
    if existing is None:
        row["Tags"] = ""
    return row


def enhancement_row(data, detachment_id=None, existing=None):
    row = dict(existing or {col: "" for col in HEADERS["Enhancements.csv"]})
    mapping = {
        "Enhancement_ID": "Enhancement_ID", "Detachment_ID": "Detachment_ID",
        "Enhancement_Name": "Enhancement_Name", "Points": "Points",
        "Short_Description": "Short_Description", "Long_Description": "Long_Description",
    }
    if detachment_id is not None:
        row["Detachment_ID"] = detachment_id
    for key, col in mapping.items():
        if key in data:
            row[col] = sval(data[key])
    if "Repeatable" in data:
        row["Repeatable"] = bool_csv(data["Repeatable"])
    elif existing is None:
        row["Repeatable"] = "FALSE"
    if existing is None:
        row["Tags"] = ""
    return row


def stratagem_row(data, detachment_id=None, existing=None):
    row = dict(existing or {col: "" for col in HEADERS["Stratagems.csv"]})
    mapping = {
        "Stratagem_ID": "Stratagem_ID", "Detachment_ID": "Detachment_ID",
        "Stratagem_Name": "Stratagem_Name", "CP_Cost": "CP_Cost",
        "Short_Description": "Short_Description", "Long_Description": "Long_Description",
    }
    if detachment_id is not None:
        row["Detachment_ID"] = detachment_id
    for key, col in mapping.items():
        if key in data:
            row[col] = sval(data[key])
    return row


def replace_weapon_abilities(state, army, weapon_id, abilities):
    table = state.t(army, "Weapon_Abilities.csv")
    table.delete_where(lambda row: row.get("Weapon_ID") == weapon_id)
    for index, ability in enumerate(abilities, start=1):
        sort_order = ability.get("Sort_Order", index)
        table.insert({
            "Weapon_ID": weapon_id,
            "Weapon_Ability_ID": f"{weapon_id}:ability_{index}",
            "Ability_Type": ability["Ability_Type"],
            "Target": ability.get("Target", ""),
            "Value": ability.get("Value", ""),
            "Condition": ability.get("Condition", ""),
            "Separator_Before": "" if index == 1 else ", ",
            "Sort_Order": sort_order,
        })


def replace_effects(state, army, source_type, source_id, effects):
    table = state.t(army, "Effects.csv")
    table.delete_where(lambda row: row.get("Source_Type") == source_type and row.get("Source_ID") == source_id)
    for index, effect in enumerate(effects, start=1):
        effect_id = sval(effect.get("Effect_ID") or f"{source_type}:{source_id}:{index}")
        if table.exists(Effect_ID=effect_id):
            fail(f"duplicate Effect_ID {effect_id!r}")
        table.insert({
            "Effect_ID": effect_id,
            "Source_Type": source_type,
            "Source_ID": source_id,
            "Effect_Type": effect["Effect_Type"],
            "Target": effect["Target"],
            "Stat": effect["Stat"],
            "Operation": effect["Operation"],
            "Value": effect["Value"],
            "Display_Tag": effect["Display_Tag"],
            "Sort_Order": effect.get("Sort_Order", index),
        })


def replace_unit_links(state, army, unit_id, payload):
    if "abilities" in payload:
        table = state.t(army, "Unit_Abilities.csv")
        table.delete_where(lambda r: r.get("Unit_ID") == unit_id and r.get("Ability_Type") == "ABILITY")
        for ability_id in payload["abilities"]:
            table.insert({"Unit_ID": unit_id, "Ability_ID": ability_id, "Ability_Type": "ABILITY"})
    if "core_abilities" in payload:
        table = state.t(army, "Unit_Abilities.csv")
        table.delete_where(lambda r: r.get("Unit_ID") == unit_id and r.get("Ability_Type") == "CORE_ABILITY")
        for ability_id in payload["core_abilities"]:
            table.insert({"Unit_ID": unit_id, "Ability_ID": ability_id, "Ability_Type": "CORE_ABILITY"})
    if "weapons" in payload:
        table = state.t(army, "Unit_Weapons.csv")
        table.delete_where(lambda r: r.get("Unit_ID") == unit_id)
        for weapon_id in payload["weapons"]:
            table.insert({"Unit_ID": unit_id, "Weapon_ID": weapon_id})
    if "points" in payload:
        table = state.t(army, "Unit_Points.csv")
        table.delete_where(lambda r: r.get("Unit_ID") == unit_id)
        for index, point in enumerate(payload["points"], start=1):
            sort_order = point.get("Sort_Order", index)
            point_id = point.get("Point_Option_ID") or f"point_{sort_order}"
            table.insert({
                "Unit_ID": unit_id,
                "Point_Option_ID": point_id,
                "Label": point.get("Label", ""),
                "Cost": point.get("Cost", ""),
                "Sort_Order": sort_order,
            })
    if "loadouts" in payload:
        delete_unit_loadouts(state, army, unit_id)
        for loadout in payload["loadouts"]:
            loadout = dict(loadout)
            loadout["Unit_ID"] = unit_id
            add_loadout(state, army, loadout)


def derived_loadout_option_id(unit_id, group_id, option_id):
    return f"{unit_id}__{group_id}__{option_id}"


def delete_unit_loadouts(state, army, unit_id):
    options = state.t(army, "Loadout_Options.csv")
    loadout_ids = {row["Loadout_Option_ID"] for row in options.rows if row.get("Unit_ID") == unit_id}
    for filename in (
        "Loadout_Weapons.csv", "Loadout_Abilities.csv", "Loadout_Points.csv",
        "Loadout_Compatibility.csv",
    ):
        state.t(army, filename).delete_where(lambda row, ids=loadout_ids: row.get("Loadout_Option_ID") in ids)
    options.delete_where(lambda row, uid=unit_id: row.get("Unit_ID") == uid)


def delete_option_children(state, army, loadout_option_id, filenames=None):
    targets = filenames or (
        "Loadout_Weapons.csv", "Loadout_Abilities.csv", "Loadout_Points.csv",
        "Loadout_Compatibility.csv",
    )
    for filename in targets:
        state.t(army, filename).delete_where(
            lambda row, lid=loadout_option_id: row.get("Loadout_Option_ID") == lid
        )


def set_default_exclusive(state, army, unit_id, group_id, loadout_option_id):
    table = state.t(army, "Loadout_Options.csv")
    for row in table.rows:
        if row.get("Unit_ID") == unit_id and row.get("Option_Group_ID") == group_id:
            row["Default"] = "TRUE" if row.get("Loadout_Option_ID") == loadout_option_id else "FALSE"


def add_loadout(state, army, data):
    options = state.t(army, "Loadout_Options.csv")
    unit_id = sval(data["Unit_ID"])
    group_id = sval(data["Option_Group_ID"])
    option_id = sval(data["Option_ID"])
    loadout_option_id = sval(
        data.get("Loadout_Option_ID") or derived_loadout_option_id(unit_id, group_id, option_id)
    )
    if options.exists(Loadout_Option_ID=loadout_option_id):
        fail(f"Loadout_Option_ID already exists: {loadout_option_id!r}")
    if options.exists(Unit_ID=unit_id, Option_Group_ID=group_id, Option_ID=option_id):
        fail(f"semantic loadout option already exists: {unit_id}/{group_id}/{option_id}")
    if not state.t(army, "Unit_Profiles.csv").exists(Unit_ID=unit_id):
        fail(f"loadout references missing Unit_ID {unit_id!r}")
    options.insert({
        "Loadout_Option_ID": loadout_option_id,
        "Unit_ID": unit_id,
        "Option_Group_ID": group_id,
        "Group_Label": data.get("Group_Label", ""),
        "Option_ID": option_id,
        "Option_Name": data["Option_Name"],
        "Default": bool_csv(data["Default"]),
        "Sort_Order": data["Sort_Order"],
    })
    if bool_csv(data["Default"]) == "TRUE":
        set_default_exclusive(state, army, unit_id, group_id, loadout_option_id)
    replace_loadout_children(state, army, loadout_option_id, data)


def replace_loadout_children(state, army, loadout_option_id, payload):
    key = {"Loadout_Option_ID": loadout_option_id}
    if "weapons" in payload:
        delete_option_children(state, army, loadout_option_id, ("Loadout_Weapons.csv",))
        table = state.t(army, "Loadout_Weapons.csv")
        for index, item in enumerate(payload["weapons"], start=1):
            table.insert({**key, "Weapon_ID": item["Weapon_ID"], "Weapon_Role": item.get("Weapon_Role", "SELECTED"), "Sort_Order": item.get("Sort_Order", index)})
    if "abilities" in payload:
        delete_option_children(state, army, loadout_option_id, ("Loadout_Abilities.csv",))
        table = state.t(army, "Loadout_Abilities.csv")
        for index, item in enumerate(payload["abilities"], start=1):
            table.insert({**key, "Ability_ID": item["Ability_ID"], "Sort_Order": item.get("Sort_Order", index)})
    if "points" in payload:
        delete_option_children(state, army, loadout_option_id, ("Loadout_Points.csv",))
        table = state.t(army, "Loadout_Points.csv")
        for index, item in enumerate(payload["points"], start=1):
            sort_order = item.get("Sort_Order", index)
            table.insert({**key, "Point_Option_ID": item.get("Point_Option_ID") or f"point_{sort_order}", "Label": item.get("Label", ""), "Cost": item.get("Cost", ""), "Sort_Order": sort_order})
    if "compatibility" in payload:
        delete_option_children(state, army, loadout_option_id, ("Loadout_Compatibility.csv",))
        table = state.t(army, "Loadout_Compatibility.csv")
        for index, item in enumerate(payload["compatibility"], start=1):
            table.insert({
                **key,
                "Required_Group_ID": item["Required_Group_ID"],
                "Compatible_Option_ID": item["Compatible_Option_ID"],
                "Rule_Order": item.get("Rule_Order", index),
                "Option_Order": item.get("Option_Order", 1),
            })

def add_unit(state, army, data):
    table = state.t(army, "Unit_Profiles.csv")
    unit_id = sval(data["Unit_ID"])
    if table.exists(Unit_ID=unit_id):
        fail(f"Unit_ID already exists: {unit_id}")
    table.insert(profile_row(data), top=True)
    replace_unit_links(state, army, unit_id, data)


def change_unit(state, army, unit_id, changes):
    table = state.t(army, "Unit_Profiles.csv")
    row = table.one(Unit_ID=unit_id)
    row.update(profile_row(changes, row))
    replace_unit_links(state, army, unit_id, changes)


def delete_unit(state, army, unit_id):
    table = state.t(army, "Unit_Profiles.csv")
    if table.delete_where(lambda r: r.get("Unit_ID") == unit_id) != 1:
        fail(f"missing Unit_ID {unit_id!r}")
    state.t(army, "Unit_Abilities.csv").delete_where(lambda r: r.get("Unit_ID") == unit_id)
    state.t(army, "Unit_Weapons.csv").delete_where(lambda r: r.get("Unit_ID") == unit_id)
    state.t(army, "Unit_Points.csv").delete_where(lambda r: r.get("Unit_ID") == unit_id)
    delete_unit_loadouts(state, army, unit_id)


def add_simple(table, id_col, row, label, top=False):
    entity_id = row[id_col]
    if table.exists(**{id_col: entity_id}):
        fail(f"{label} already exists: {entity_id}")
    table.insert(row, top=top)


def delete_simple(table, id_col, entity_id, label):
    if table.delete_where(lambda r: r.get(id_col) == entity_id) != 1:
        fail(f"missing {label} {entity_id!r}")


def apply_operation(state, op, index):
    mode = op["operation"]
    entity = op["entity_type"]
    army = op["army"]
    ensure_entity_army(entity, army)
    data = op.get("data")
    changes = op.get("changes")
    entity_id = op.get("id")
    if mode == "add":
        validate_new_display_names(data)
        for field in PRIMARY_ADD_IDS.get(entity, ()):
            if field in data:
                validate_new_entity_id(data[field], field)
        if entity == "detachment":
            for enhancement in data.get("enhancements", []):
                validate_new_entity_id(enhancement["Enhancement_ID"], "Enhancement_ID")
            for stratagem in data.get("stratagems", []):
                validate_new_entity_id(stratagem["Stratagem_ID"], "Stratagem_ID")
    print(f"op {index}: {mode} {entity} [{army}]")

    if entity == "unit":
        if mode == "add": add_unit(state, army, data)
        elif mode == "change": change_unit(state, army, sval(entity_id), changes)
        else: delete_unit(state, army, sval(entity_id))
        return

    if entity == "weapon":
        table = state.t(army, "Weapon_Stats.csv")
        if mode == "add":
            wid = sval(data["Weapon_ID"])
            add_simple(table, "Weapon_ID", weapon_row(data), "Weapon_ID")
            if "weapon_abilities" in data:
                replace_weapon_abilities(state, army, wid, data["weapon_abilities"])
        elif mode == "change":
            wid = sval(entity_id)
            row = table.one(Weapon_ID=wid)
            row.update(weapon_row(changes, row))
            if "weapon_abilities" in changes:
                replace_weapon_abilities(state, army, wid, changes["weapon_abilities"])
        else:
            wid = sval(entity_id)
            delete_simple(table, "Weapon_ID", wid, "Weapon_ID")
            state.t(army, "Weapon_Abilities.csv").delete_where(lambda r: r.get("Weapon_ID") == wid)
            state.t(army, "Unit_Weapons.csv").delete_where(lambda r: r.get("Weapon_ID") == wid)
            state.t(army, "Loadout_Weapons.csv").delete_where(lambda r: r.get("Weapon_ID") == wid)
        return

    if entity == "ability":
        table = state.t(army, "Abilities.csv")
        if mode == "add":
            add_simple(table, "Ability_ID", ability_row(data), "Ability_ID")
            if "effects" in data: replace_effects(state, army, "ABILITY", sval(data["Ability_ID"]), data["effects"])
        elif mode == "change":
            aid = sval(entity_id); row = table.one(Ability_ID=aid); row.update(ability_row(changes, row))
            if "effects" in changes: replace_effects(state, army, "ABILITY", aid, changes["effects"])
        else:
            aid = sval(entity_id); delete_simple(table, "Ability_ID", aid, "Ability_ID")
            state.t(army, "Unit_Abilities.csv").delete_where(lambda r: r.get("Ability_ID") == aid)
            state.t(army, "Loadout_Abilities.csv").delete_where(lambda r: r.get("Ability_ID") == aid)
            state.t(army, "Effects.csv").delete_where(lambda r: r.get("Source_Type") == "ABILITY" and r.get("Source_ID") == aid)
        return

    if entity == "detachment":
        table = state.t(army, "Detachment_Definitions.csv")
        if mode == "add":
            did = sval(data["Detachment_ID"])
            add_simple(table, "Detachment_ID", {
                "Detachment_ID": did, "Army_Name": state.army_name(army), "Detachment_Name": data["Detachment_Name"],
                "Rule_ID": data["Rule_ID"], "Rule_Name": data["Rule_Name"], "DP_Cost": data.get("DP_Cost", ""),
                "Detachment_Disposition": data.get("Detachment_Disposition", ""), "Detachment_Disposition_2": data.get("Detachment_Disposition_2", ""),
                "Short_Description": data.get("Short_Description", ""), "Long_Description": data.get("Long_Description", ""),
            }, "Detachment_ID")
            for enh in data.get("enhancements", []):
                add_enhancement(state, army, enh, did)
            for strat in data.get("stratagems", []):
                add_stratagem(state, army, strat, did)
        elif mode == "change":
            did = sval(entity_id); row = table.one(Detachment_ID=did)
            mapping = {"Detachment_Name":"Detachment_Name","Rule_ID":"Rule_ID","Rule_Name":"Rule_Name","DP_Cost":"DP_Cost","Detachment_Disposition":"Detachment_Disposition","Detachment_Disposition_2":"Detachment_Disposition_2","Short_Description":"Short_Description","Long_Description":"Long_Description"}
            for key, col in mapping.items():
                if key in changes: row[col] = sval(changes[key])
        else:
            did = sval(entity_id); delete_simple(table, "Detachment_ID", did, "Detachment_ID")
            enh_table = state.t(army, "Enhancements.csv")
            enh_ids = {r.get("Enhancement_ID") for r in enh_table.rows if r.get("Detachment_ID") == did}
            enh_table.delete_where(lambda r: r.get("Detachment_ID") == did)
            state.t(army, "Stratagems.csv").delete_where(lambda r: r.get("Detachment_ID") == did)
            state.t(army, "Effects.csv").delete_where(lambda r: r.get("Source_Type") == "ENHANCEMENT" and r.get("Source_ID") in enh_ids)
        return

    if entity == "enhancement":
        if mode == "add": add_enhancement(state, army, data)
        elif mode == "change": change_enhancement(state, army, sval(entity_id), changes)
        else: delete_enhancement(state, army, sval(entity_id))
        return

    if entity == "stratagem":
        if mode == "add": add_stratagem(state, army, data)
        elif mode == "change":
            table = state.t(army, "Stratagems.csv"); sid = sval(entity_id); row = table.one(Stratagem_ID=sid); row.update(stratagem_row(changes, existing=row))
        else: delete_simple(state.t(army, "Stratagems.csv"), "Stratagem_ID", sval(entity_id), "Stratagem_ID")
        return

    if entity == "army_rule":
        table = state.t(army, "Army_Rules.csv")
        if mode == "add":
            add_simple(table, "Army_Rule_ID", {"Army_Rule_ID":data["Army_Rule_ID"],"Army_Name":state.army_name(army),"Rule_Name":data["Rule_Name"],"Short_Description":data.get("Short_Description", ""),"Long_Description":data.get("Long_Description", "")}, "Army_Rule_ID")
        elif mode == "change":
            row = table.one(Army_Rule_ID=sval(entity_id))
            for key, col in {"Rule_Name":"Rule_Name","Short_Description":"Short_Description","Long_Description":"Long_Description"}.items():
                if key in changes: row[col] = sval(changes[key])
        else: delete_simple(table, "Army_Rule_ID", sval(entity_id), "Army_Rule_ID")
        return

    if entity == "effect":
        table = state.t(army, "Effects.csv")
        if mode == "add":
            row = {col: sval(data.get(col, "")) for col in HEADERS["Effects.csv"]}
            if not row["Sort_Order"]: row["Sort_Order"] = "1"
            add_simple(table, "Effect_ID", row, "Effect_ID")
        elif mode == "change":
            row = table.one(Effect_ID=sval(entity_id))
            for key in HEADERS["Effects.csv"]:
                if key != "Effect_ID" and key in changes: row[key] = sval(changes[key])
        else: delete_simple(table, "Effect_ID", sval(entity_id), "Effect_ID")
        return

    if entity == "loadout_option":
        if mode == "add":
            add_loadout(state, army, data)
        else:
            loadout_option_id = sval(entity_id)
            table = state.t(army, "Loadout_Options.csv")
            if mode == "change":
                row = table.one(Loadout_Option_ID=loadout_option_id)
                for key_name, col in {"Group_Label":"Group_Label","Option_Name":"Option_Name","Default":"Default","Sort_Order":"Sort_Order"}.items():
                    if key_name in changes:
                        row[col] = bool_csv(changes[key_name]) if key_name == "Default" else sval(changes[key_name])
                if changes.get("Default") is True or str(changes.get("Default", "")).lower() in {"true","1","yes","y"}:
                    set_default_exclusive(state, army, row["Unit_ID"], row["Option_Group_ID"], loadout_option_id)
                replace_loadout_children(state, army, loadout_option_id, changes)
            else:
                if table.delete_where(lambda r, lid=loadout_option_id: r.get("Loadout_Option_ID") == lid) != 1:
                    fail(f"missing Loadout_Option_ID {loadout_option_id!r}")
                delete_option_children(state, army, loadout_option_id)
        return

    if entity == "universal_ability":
        table = state.t(UNIVERSAL, "Universal_Abilities.csv")
        if mode == "add":
            add_simple(table, "Ability_ID", {"Ability_ID":data["Ability_ID"],"Ability Name":data["Ability_Name"],"Short_Description":data.get("Short_Description", ""),"Long_Description":data.get("Long_Description", ""),"Order":data.get("Order", "")}, "universal Ability_ID")
        elif mode == "change":
            row = table.one(Ability_ID=sval(entity_id))
            for key, col in {"Ability_Name":"Ability Name","Short_Description":"Short_Description","Long_Description":"Long_Description","Order":"Order"}.items():
                if key in changes: row[col] = sval(changes[key])
        else:
            aid = sval(entity_id); delete_simple(table, "Ability_ID", aid, "universal Ability_ID")
            for a in ARMIES:
                state.t(a, "Unit_Abilities.csv").delete_where(lambda r, x=aid: r.get("Ability_ID") == x)
                state.t(a, "Loadout_Abilities.csv").delete_where(lambda r, x=aid: r.get("Ability_ID") == x)
        return

    if entity == "universal_stratagem":
        table = state.t(UNIVERSAL, "Universal_Stratagems.csv")
        if mode == "add":
            row = {"Detachment_ID":data["Detachment_ID"],"Detachment_Name":data.get("Detachment_Name", ""),"Item_Type":data["Item_Type"],"Item_ID":data["Item_ID"],"Item_Name":data["Item_Name"],"Points":data.get("Points", ""),"CP_Cost":data.get("CP_Cost", ""),"Short_Description":data.get("Short_Description", ""),"Long_Description":data.get("Long_Description", "")}
            add_simple(table, "Item_ID", row, "universal Item_ID")
        elif mode == "change":
            row = table.one(Item_ID=sval(entity_id))
            mapping = {"Detachment_ID":"Detachment_ID","Detachment_Name":"Detachment_Name","Item_Type":"Item_Type","Item_Name":"Item_Name","Points":"Points","CP_Cost":"CP_Cost","Short_Description":"Short_Description","Long_Description":"Long_Description"}
            for key, col in mapping.items():
                if key in changes: row[col] = sval(changes[key])
        else: delete_simple(table, "Item_ID", sval(entity_id), "universal Item_ID")
        return

    fail(f"unsupported entity_type {entity!r}")


def add_enhancement(state, army, data, detachment_id=None):
    table = state.t(army, "Enhancements.csv")
    row = enhancement_row(data, detachment_id=detachment_id)
    did = row["Detachment_ID"]
    if not state.t(army, "Detachment_Definitions.csv").exists(Detachment_ID=did):
        fail(f"Enhancement references missing Detachment_ID {did!r}")
    add_simple(table, "Enhancement_ID", row, "Enhancement_ID")
    if "effects" in data: replace_effects(state, army, "ENHANCEMENT", row["Enhancement_ID"], data["effects"])


def change_enhancement(state, army, enhancement_id, changes):
    table = state.t(army, "Enhancements.csv")
    row = table.one(Enhancement_ID=enhancement_id)
    row.update(enhancement_row(changes, existing=row))
    if "effects" in changes: replace_effects(state, army, "ENHANCEMENT", enhancement_id, changes["effects"])


def delete_enhancement(state, army, enhancement_id):
    delete_simple(state.t(army, "Enhancements.csv"), "Enhancement_ID", enhancement_id, "Enhancement_ID")
    state.t(army, "Effects.csv").delete_where(lambda r: r.get("Source_Type") == "ENHANCEMENT" and r.get("Source_ID") == enhancement_id)


def add_stratagem(state, army, data, detachment_id=None):
    row = stratagem_row(data, detachment_id=detachment_id)
    did = row["Detachment_ID"]
    if not state.t(army, "Detachment_Definitions.csv").exists(Detachment_ID=did):
        fail(f"Stratagem references missing Detachment_ID {did!r}")
    add_simple(state.t(army, "Stratagems.csv"), "Stratagem_ID", row, "Stratagem_ID")


def validate_state(state):
    universal_abilities = idset(state.t(UNIVERSAL, "Universal_Abilities.csv"), "Ability_ID")
    for army in ARMIES:
        profiles = state.t(army, "Unit_Profiles.csv")
        weapons = state.t(army, "Weapon_Stats.csv")
        weapon_abilities = state.t(army, "Weapon_Abilities.csv")
        abilities = state.t(army, "Abilities.csv")
        detachments = state.t(army, "Detachment_Definitions.csv")
        enhancements = state.t(army, "Enhancements.csv")
        stratagems = state.t(army, "Stratagems.csv")
        effects = state.t(army, "Effects.csv")
        options = state.t(army, "Loadout_Options.csv")
        unique(profiles, ["Unit_ID"], f"{army} Unit_ID")
        unique(weapons, ["Weapon_ID"], f"{army} Weapon_ID")
        unique(weapon_abilities, ["Weapon_Ability_ID"], f"{army} Weapon_Ability_ID")
        unique(weapon_abilities, ["Weapon_ID", "Sort_Order"], f"{army} weapon ability sort order")
        unique(abilities, ["Ability_ID"], f"{army} Ability_ID")
        unique(detachments, ["Detachment_ID"], f"{army} Detachment_ID")
        unique(detachments, ["Rule_ID"], f"{army} Rule_ID")
        unique(enhancements, ["Enhancement_ID"], f"{army} Enhancement_ID")
        unique(stratagems, ["Stratagem_ID"], f"{army} Stratagem_ID")
        unique(effects, ["Effect_ID"], f"{army} Effect_ID")
        unique(options, ["Loadout_Option_ID"], f"{army} Loadout_Option_ID")
        unique(options, ["Unit_ID", "Option_Group_ID", "Option_ID"], f"{army} semantic loadout option")
        unit_ids = idset(profiles, "Unit_ID")
        weapon_ids = idset(weapons, "Weapon_ID")
        ability_ids = idset(abilities, "Ability_ID") | universal_abilities
        for row in weapon_abilities.rows:
            if row["Weapon_ID"] not in weapon_ids:
                fail(f"{army}: Weapon_Abilities missing Weapon_ID {row['Weapon_ID']!r}")
            if not (row.get("Ability_Type") or "").strip():
                fail(f"{army}: Weapon_Abilities blank Ability_Type for {row['Weapon_Ability_ID']!r}")
            if row["Ability_Type"] == "ANTI" and (not row["Target"] or not row["Value"]):
                fail(f"{army}: ANTI weapon ability requires Target and Value for {row['Weapon_Ability_ID']!r}")

        detachment_ids = idset(detachments, "Detachment_ID")
        enhancement_ids = idset(enhancements, "Enhancement_ID")
        army_ability_ids = idset(abilities, "Ability_ID")

        for row in state.t(army, "Unit_Abilities.csv").rows:
            if row["Unit_ID"] not in unit_ids: fail(f"{army}: Unit_Abilities missing Unit_ID {row['Unit_ID']!r}")
            if row["Ability_ID"] not in ability_ids: fail(f"{army}: Unit_Abilities missing Ability_ID {row['Ability_ID']!r}")
        for row in state.t(army, "Unit_Weapons.csv").rows:
            if row["Unit_ID"] not in unit_ids: fail(f"{army}: Unit_Weapons missing Unit_ID {row['Unit_ID']!r}")
            if row["Weapon_ID"] not in weapon_ids: fail(f"{army}: Unit_Weapons missing Weapon_ID {row['Weapon_ID']!r}")
        for row in state.t(army, "Unit_Points.csv").rows:
            if row["Unit_ID"] not in unit_ids: fail(f"{army}: Unit_Points missing Unit_ID {row['Unit_ID']!r}")
        for row in enhancements.rows:
            if row["Detachment_ID"] not in detachment_ids: fail(f"{army}: enhancement missing Detachment_ID {row['Detachment_ID']!r}")
        for row in stratagems.rows:
            if row["Detachment_ID"] not in detachment_ids: fail(f"{army}: stratagem missing Detachment_ID {row['Detachment_ID']!r}")
        for row in effects.rows:
            st, sid = row["Source_Type"], row["Source_ID"]
            if st == "ABILITY" and sid not in army_ability_ids: fail(f"{army}: effect missing Ability_ID source {sid!r}")
            if st == "ENHANCEMENT" and sid not in enhancement_ids: fail(f"{army}: effect missing Enhancement_ID source {sid!r}")
            if st not in {"ABILITY", "ENHANCEMENT"}: fail(f"{army}: invalid effect Source_Type {st!r}")

        loadout_ids = {r["Loadout_Option_ID"] for r in options.rows}
        group_options = {}
        for row in options.rows:
            if row["Unit_ID"] not in unit_ids:
                fail(f"{army}: loadout missing Unit_ID {row['Unit_ID']!r}")
            group_options.setdefault((row["Unit_ID"], row["Option_Group_ID"]), set()).add(row["Option_ID"])
        child_specs = [
            ("Loadout_Weapons.csv", "Weapon_ID", weapon_ids),
            ("Loadout_Abilities.csv", "Ability_ID", ability_ids),
            ("Loadout_Points.csv", None, None),
            ("Loadout_Compatibility.csv", None, None),
        ]
        for filename, ref_col, valid_ids in child_specs:
            for row in state.t(army, filename).rows:
                lid = row["Loadout_Option_ID"]
                if lid not in loadout_ids:
                    fail(f"{army}: {filename} references missing Loadout_Option_ID {lid!r}")
                if ref_col and row[ref_col] not in valid_ids:
                    fail(f"{army}: {filename} missing {ref_col} {row[ref_col]!r}")
        option_by_id = {r["Loadout_Option_ID"]: r for r in options.rows}
        for row in state.t(army, "Loadout_Compatibility.csv").rows:
            parent = option_by_id[row["Loadout_Option_ID"]]
            target = group_options.get((parent["Unit_ID"], row["Required_Group_ID"]), set())
            if row["Compatible_Option_ID"] not in target:
                fail(
                    f"{army}: compatibility for {row['Loadout_Option_ID']!r} references "
                    f"unknown {row['Required_Group_ID']}/{row['Compatible_Option_ID']}"
                )

    unique(state.t(UNIVERSAL, "Universal_Abilities.csv"), ["Ability_ID"], "universal Ability_ID")
    unique(state.t(UNIVERSAL, "Universal_Stratagems.csv"), ["Item_ID"], "universal Item_ID")


def load_payload(args):
    if args.file:
        raw = Path(args.file).read_text(encoding="utf-8")
    else:
        raw = os.environ.get(args.env, "")
    if not raw.strip():
        fail("empty entity operations payload")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        fail(f"entity operations payload is not valid JSON: {exc}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file")
    parser.add_argument("--env", default="ENTITY_OPS_JSON")
    args = parser.parse_args()
    payload = load_payload(args)
    schema_validate(payload)
    operations = payload["operations"]
    state = State()
    for index, op in enumerate(operations, start=1):
        apply_operation(state, op, index)
    validate_state(state)
    changed = state.write_changed()
    if operations and not changed:
        fail("operations produced no canonical data changes")
    print("entity ops canonical changes:", ", ".join(changed) if changed else "none (validation-only)")


if __name__ == "__main__":
    main()
