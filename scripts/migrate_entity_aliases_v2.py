#!/usr/bin/env python3
from pathlib import Path

import migrate_entity_aliases_v1 as migration

ROOT = Path(__file__).resolve().parents[1]


def ensure_entity_ops_re_import():
    path = ROOT / "scripts" / "entity_ops.py"
    text = path.read_text(encoding="utf-8")
    if "import re\n" not in text:
        anchor = "import os\n"
        if anchor not in text:
            migration.fail("entity_ops.py import anchor not found")
        text = text.replace(anchor, anchor + "import re\n", 1)
        path.write_text(text, encoding="utf-8")
    print("entity_ops.py: regex support ready")


def write_no_new_validator():
    path = ROOT / "scripts" / "validate_no_new_names.py"
    content = r'''#!/usr/bin/env python3
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEW_ID_RE = re.compile(r"(?:^NEW(?:_|$)|_NEW(?:_|$)|\(New\))", re.IGNORECASE)
NEW_NAME_RE = re.compile(r"\(\s*New\s*\)", re.IGNORECASE)
LEGACY_EXEMPT_COLUMNS = {"Legacy_Unit_ID", "Legacy_Unit_IDs", "Alias_ID"}


def fail(message):
    raise SystemExit(message)


def main():
    issues = []
    for path in sorted((ROOT / "data").rglob("*.csv")):
        if path.name == "Entity_Aliases.csv":
            continue
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for line_no, row in enumerate(reader, start=2):
                for column, value in row.items():
                    text = (value or "").strip()
                    if not text or column in LEGACY_EXEMPT_COLUMNS:
                        continue
                    is_id = column == "Item_ID" or column.endswith("_ID") or column in {"Ability_ID", "Weapon_ID", "Unit_ID"}
                    is_name = column.endswith("Name") or column.endswith("_Name") or column in {"Ability Name", "Weapon Name", "Unit Name"}
                    if is_id and NEW_ID_RE.search(text):
                        issues.append(f"{path.relative_to(ROOT)}:{line_no}:{column}={text}")
                    if is_name and NEW_NAME_RE.search(text):
                        issues.append(f"{path.relative_to(ROOT)}:{line_no}:{column}={text}")
    if issues:
        fail("New naming remains outside hidden compatibility aliases:\n" + "\n".join(issues))
    print("New-name audit: OK — no canonical or visible '(New)' / NEW_* identifiers")


if __name__ == "__main__":
    main()
'''
    path.write_text(content, encoding="utf-8")
    print("validate_no_new_names.py: created")


def main():
    aliases = []
    migration.migrate_universal_abilities(aliases)
    migration.migrate_units(aliases)
    migration.replace_universal_ability_references()
    migration.write_alias_file(aliases)
    migration.patch_csv_schema()
    migration.write_alias_validator()
    write_no_new_validator()
    ensure_entity_ops_re_import()
    migration.patch_entity_ops()
    migration.patch_json_schema()
    print("entity alias migration v2: OK")


if __name__ == "__main__":
    main()
