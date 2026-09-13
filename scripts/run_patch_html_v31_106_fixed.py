from pathlib import Path

patch_path = Path('scripts/patch_html_v31_106.py')
source = patch_path.read_text(encoding='utf-8')

old = '''def once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)
'''
new = '''def once(old, new, label):
    global text, view_np
    if 'view_np' in globals():
        view_count = view_np.count(old)
        if view_count == 1:
            view_np = view_np.replace(old, new, 1)
            return
        if view_count > 1:
            raise SystemExit(f'{label}: expected 1 View match, found {view_count}')
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)
'''

if source.count(old) != 1:
    raise SystemExit('V31.106 helper block changed; refusing to rewrite it')
source = source.replace(old, new, 1)
exec(compile(source, str(patch_path), 'exec'), {'__name__': '__main__'})
