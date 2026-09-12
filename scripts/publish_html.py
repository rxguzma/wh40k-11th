"""Archive the canonical standalone app and atomically regenerate its release index."""
import argparse
import json
import re
from pathlib import Path

VERSION = re.compile(r'const APP_VERSION = "(\d+\.\d+(?:\.\d+)*)";')
FILENAME = re.compile(r'WH40k_11th_V(\d+\.\d+(?:\.\d+)*)\.html')


def key(version):
    return tuple(map(int, version.split('.')))


def inspect_html(content):
    text = content.decode('utf-8')
    matches = VERSION.findall(text)
    if len(matches) != 1:
        raise ValueError('Expected exactly one APP_VERSION declaration')
    version = matches[0]
    for marker in (f'<title>WH40k 11th V{version}</title>', 'id="wh40k-runtime"', 'id="wh40k-version-host"'):
        if marker not in text:
            raise ValueError(f'Missing release marker: {marker}')
    if not text.lstrip().lower().startswith('<!doctype html>') or not text.rstrip().lower().endswith('</html>'):
        raise ValueError('Incomplete standalone HTML')
    return version


def publish(root):
    canonical = root / 'WH40k_11th.html'
    content = canonical.read_bytes()
    version = inspect_html(content)
    directory = root / 'versions'
    directory.mkdir(exist_ok=True)
    target = directory / f'WH40k_11th_V{version}.html'
    existing = []
    for path in directory.glob('WH40k_11th_V*.html'):
        match = FILENAME.fullmatch(path.name)
        if not match:
            raise ValueError(f'Invalid release filename: {path.name}')
        other = match[1]
        if inspect_html(path.read_bytes()) != other:
            raise ValueError(f'HTML version does not match {path.name}')
        existing.append((other, path))
    if existing and key(version) < max(key(v) for v, _ in existing):
        raise ValueError('Canonical version must not be older than the newest retained release')
    if target.exists() and target.read_bytes() != content:
        raise ValueError('Published version already exists with different content; advance the version')
    # Validate everything before changing or deleting any retained release.
    target.write_bytes(content)
    retained = sorted([(v, p) for v, p in existing if p != target] + [(version, target)], key=lambda x: key(x[0]), reverse=True)
    for _, path in retained[10:]:
        path.unlink()
    retained = retained[:10]
    index = {'latest': version, 'versions': [{'version': v, 'file': f'versions/{p.name}'} for v, p in retained]}
    temporary = directory / 'index.json.tmp'
    temporary.write_text(json.dumps(index, indent=2) + '\n')
    temporary.replace(directory / 'index.json')
    return index


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    result = publish(args.root)
    print(f"Published v{result['latest']}; retained {len(result['versions'])} version(s)")
