#!/usr/bin/env python3
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

path = ROOT / "scripts" / "validate_loadouts.py"
text = path.read_text(encoding="utf-8")
text = text.replace("        [\n        [],\n    )", "        [],\n    )")
path.write_text(text, encoding="utf-8")
print("fixed validate_loadouts legacy-list transform")

path = ROOT / "scripts" / "entity_ops.py"
text = path.read_text(encoding="utf-8")
text = re.sub(r'^\s*\(None, None\),\n', '', text, flags=re.MULTILINE)
path.write_text(text, encoding="utf-8")
print("fixed Entity Ops child-spec transform")
