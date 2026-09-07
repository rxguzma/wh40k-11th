#!/usr/bin/env python3
import base64, gzip, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
assets = [
    (ROOT / 'scripts/.entity_ops.py.gz.b64', ROOT / 'scripts/entity_ops.py'),
    (ROOT / 'schemas/.entity-ops.schema.json.gz.b64', ROOT / 'schemas/entity-ops.schema.json'),
]
for source, target in assets:
    raw = base64.b64decode(source.read_text(encoding='utf-8').strip())
    content = gzip.decompress(raw)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    print(f'installed {target.relative_to(ROOT)} ({len(content)} bytes)')
json.loads((ROOT / 'schemas/entity-ops.schema.json').read_text(encoding='utf-8'))
print('Entity Ops assets installed and JSON schema parsed')
