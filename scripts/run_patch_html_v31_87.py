from pathlib import Path

patch_path = Path('scripts/patch_html_v31_87.py')
source = patch_path.read_text(encoding='utf-8')
needle = '# Write both embedded pages back.'
cleanup = r'''# Remove any remaining obsolete authored first/second-row CSS selectors.
# Dynamic roster rows use inline grid-row placement, so these selectors are no
# longer part of either New View or New Edit.
for fixed_class in ('view-unit-row-first','view-unit-row-second','edit-unit-row-first','edit-unit-row-second'):
    css_rule = re.compile(r'\.' + re.escape(fixed_class) + r'\{[^}]*\}')
    view_np = css_rule.sub('', view_np)
    edit_np = css_rule.sub('', edit_np)

for token in ('.view-unit-row-first','.view-unit-row-second','.edit-unit-row-first','.edit-unit-row-second'):
    for label, doc in (('VIEW', view_np), ('EDIT', edit_np)):
        pos = doc.find(token)
        if pos >= 0:
            print('REMAINING', label, token, repr(doc[max(0,pos-120):pos+220]))

'''
if source.count(needle) != 1:
    raise SystemExit('V31.87 writeback marker missing')
source = source.replace(needle, cleanup + needle, 1)
exec(compile(source, str(patch_path), 'exec'), {'__name__': '__main__'})
