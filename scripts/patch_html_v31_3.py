from pathlib import Path
import re
import subprocess

path = Path('WH40k_11th.html')
text = path.read_text(encoding='utf-8')


def replace_once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


# Version.
replace_once('<title>WH40k 11th V31.2</title>', '<title>WH40k 11th V31.3</title>', 'title')
replace_once('const APP_VERSION = "31.2";', 'const APP_VERSION = "31.3";', 'APP_VERSION')
replace_once("version: 'V31.2',", "version: 'V31.3',", 'InternalQuality version')
replace_once('current baseline is WH40k_11th_V31.2', 'current baseline is WH40k_11th_V31.3', 'maintenance baseline')

# New add-panel buttons use the same compact type scale as the category tabs.
css_old = '''    .view-edit-unit-add-option {
      min-width: 0;
      height: auto;
      padding: 9px 4px;
      line-height: 1.15;
      white-space: normal;
      overflow-wrap: anywhere;
    }
'''
css_new = '''    .view-edit-unit-add-option {
      min-width: 0;
      height: auto;
      padding: 9px 4px;
      font-size: var(--font-meta);
      line-height: 1.15;
      white-space: normal;
      overflow-wrap: anywhere;
    }
'''
replace_once(css_old, css_new, 'add-panel font size')

# Selected choices must use the standard success-green state, not the category active color.
selected_old = 'class="category-button view-edit-unit-add-option${selected ? " active" : ""}"'
selected_new = 'class="category-button view-edit-unit-add-option${selected ? " green" : ""}"'
selected_count = text.count(selected_old)
if selected_count != 2:
    raise SystemExit(f'selected button classes: expected 2 matches, found {selected_count}')
text = text.replace(selected_old, selected_new)

# The View renderer cannot use refreshViewEditEntryExpandedState because that helper is Edit-only.
add_toggle_old = '''      toggleViewEditRosterAddPanel(entryId) {
        if (!entryId) return;
        viewEditExpandedUnitRows[entryId] = true;
        const sections = getViewEditEntrySections(entryId);
        sections.add = !sections.add;
        RosterRender.refreshViewEditEntryExpandedState(entryId);
      },'''
add_toggle_new = '''      toggleViewEditRosterAddPanel(entryId) {
        if (!entryId) return;
        viewEditExpandedUnitRows[entryId] = true;
        const sections = getViewEditEntrySections(entryId);
        sections.add = !sections.add;
        RosterRender.refreshViewEditRosterDom();
      },'''
replace_once(add_toggle_old, add_toggle_new, 'View/Edit + toggle refresh')

# Keep faction eligibility generic in the matcher by declaring the faction keyword in source config.
for army_key, faction_keyword in (
    ('Marines', 'ADEPTUS ASTARTES'),
    ('Nids', 'TYRANIDS'),
    ('Orks', 'ORKS'),
):
    old = f'''      {army_key}: {{\n        type: "army",'''
    new = f'''      {army_key}: {{\n        type: "army",\n        factionKeyword: "{faction_keyword}",'''
    replace_once(old, new, f'{army_key} faction keyword')

matcher_old = '''      const effective = getEffectiveUnitProfile(entry, unit, roster);
      const unitKeywords = new Set((effective && Array.isArray(effective.keywords) ? effective.keywords : getKeywordsForUnit(unit)).map(normalizeEligibilityKeyword).filter(Boolean));
      const required = parseEligibilityKeywordList(getDetachmentItemEligibilityValue(item, "Required_Keywords"));'''
matcher_new = '''      const effective = getEffectiveUnitProfile(entry, unit, roster);
      const unitKeywords = new Set((effective && Array.isArray(effective.keywords) ? effective.keywords : getKeywordsForUnit(unit)).map(normalizeEligibilityKeyword).filter(Boolean));
      const sourceConfig = getDataSourceConfig(activeArmyKey);
      const factionKeyword = normalizeEligibilityKeyword(sourceConfig && sourceConfig.factionKeyword);
      if (factionKeyword) unitKeywords.add(factionKeyword);
      const required = parseEligibilityKeywordList(getDetachmentItemEligibilityValue(item, "Required_Keywords"));'''
replace_once(matcher_old, matcher_new, 'faction keyword matcher')

# Release note, then retain only the five newest detailed notes.
note_anchor = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.2'''
note_new = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.3
    Scope: Fix the Unit + add panel. Choice buttons now use compact 12px/meta typography and standard success-green selected state. The + panel now rerenders in both View and Edit, so View opens eligible Stratagems correctly. Eligibility also receives each source's configured faction keyword (ADEPTUS ASTARTES, TYRANIDS, ORKS) without faction-specific branching in the matcher.
    Risk areas: Unit detail rerendering and keyword eligibility only. Existing Tags/Probable mechanics and unrelated roster behavior are unchanged.
  -->

  <!--
    CHANGE NOTE - WH40k_11th_V31.2'''
replace_once(note_anchor, note_new, 'V31.3 release note')

note_pattern = re.compile(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V[^\n]+\n.*?\n  -->\n', re.S)
notes = list(note_pattern.finditer(text))
if len(notes) != 6:
    raise SystemExit(f'release notes: expected 6 after insertion, found {len(notes)}')
oldest = notes[-1]
text = text[:oldest.start()] + '\n' + text[oldest.end():]

path.write_text(text, encoding='utf-8')

# Static regression checks.
text = path.read_text(encoding='utf-8')
assert '<title>WH40k 11th V31.3</title>' in text
assert text.count('const APP_VERSION = "31.3";') == 1
assert "version: 'V31.3'," in text
assert text.count('CHANGE NOTE - WH40k_11th_') == 5
assert text.count('font-size: var(--font-meta);\n      line-height: 1.15;') == 1
assert text.count('view-edit-unit-add-option${selected ? " green" : ""}') == 2
assert 'toggleViewEditRosterAddPanel(entryId)' in text
assert 'sections.add = !sections.add;\n        RosterRender.refreshViewEditRosterDom();' in text
assert 'factionKeyword: "ADEPTUS ASTARTES"' in text
assert 'factionKeyword: "TYRANIDS"' in text
assert 'factionKeyword: "ORKS"' in text
assert 'if (factionKeyword) unitKeywords.add(factionKeyword);' in text

runtime = re.search(r'<script id="wh40k-runtime" type="text/wh40k-runtime">(.*?)</script>', text, re.S)
if not runtime:
    raise SystemExit('runtime script not found')
Path('/tmp/wh40k-runtime.js').write_text(runtime.group(1), encoding='utf-8')
subprocess.run(['node', '--check', '/tmp/wh40k-runtime.js'], check=True)
print('V31.3 plus-panel regression checks passed')
