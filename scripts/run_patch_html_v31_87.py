from pathlib import Path

patch_path = Path('scripts/patch_html_v31_87.py')
source = patch_path.read_text(encoding='utf-8')
needle = '# Write both embedded pages back.'
cleanup = r'''# Remove obsolete authored first/second-row CSS selectors and convert the
# remaining first-Unit active selectors to the generic Unit-row selector.
for fixed_class in ('view-unit-row-first','view-unit-row-second','edit-unit-row-first','edit-unit-row-second'):
    css_rule = re.compile(r'\.' + re.escape(fixed_class) + r'\{[^}]*\}')
    view_np = css_rule.sub('', view_np)
    edit_np = css_rule.sub('', edit_np)

view_np = view_np.replace('.view-unit-row-first.unit-active', '.view-unit-row.unit-active')
edit_np = edit_np.replace('.view-unit-row-first.unit-active', '.view-unit-row.unit-active')

'''
if source.count(needle) != 1:
    raise SystemExit('V31.87 writeback marker missing')
source = source.replace(needle, cleanup + needle, 1)
exec(compile(source, str(patch_path), 'exec'), {'__name__': '__main__'})
