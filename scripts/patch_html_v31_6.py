from pathlib import Path
import csv
import io
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
html_path = ROOT / 'WH40k_11th.html'
schema_path = ROOT / 'data' / 'CSV_SCHEMA.csv'
rules_path = ROOT / 'data' / 'universal' / 'Eligibility_Rules.csv'

text = html_path.read_text(encoding='utf-8')

# Version.
for old, new in (
    ('<title>WH40k 11th V31.5</title>', '<title>WH40k 11th V31.6</title>'),
    ('current baseline is WH40k_11th_V31.5;', 'current baseline is WH40k_11th_V31.6;'),
    ('const APP_VERSION = "31.5";', 'const APP_VERSION = "31.6";'),
    ("version: 'V31.5',", "version: 'V31.6',"),
):
    if old not in text:
        raise SystemExit(f'missing version anchor: {old}')
    text = text.replace(old, new, 1)

# Universal category eligibility is a required data source.
old_required = 'requiredTabs: ["Abilities", "Stratagems", "Tag_Definitions", "Dispositions", "Primary_Missions", "Primary_Mission_Matchups"],'
new_required = 'requiredTabs: ["Abilities", "Stratagems", "Tag_Definitions", "Eligibility_Rules", "Dispositions", "Primary_Missions", "Primary_Mission_Matchups"],'
if old_required not in text:
    raise SystemExit('Universal requiredTabs anchor missing')
text = text.replace(old_required, new_required, 1)

old_tag_url = '          "Tag_Definitions": "https://raw.githubusercontent.com/rxguzma/wh40k-11th/main/data/universal/Tag_Definitions.csv",'
new_tag_url = old_tag_url + '\n          "Eligibility_Rules": "https://raw.githubusercontent.com/rxguzma/wh40k-11th/main/data/universal/Eligibility_Rules.csv",'
if old_tag_url not in text:
    raise SystemExit('Universal Tag_Definitions URL anchor missing')
text = text.replace(old_tag_url, new_tag_url, 1)

old_header = '      "Tag_Definitions": Object.freeze({ file: "Tag_Definitions.csv", columns: Object.freeze(["Tag_ID", "Display_Tag", "Category", "Editable", "Sort_Order"]) }),' 
new_header = old_header + '\n      "Eligibility_Rules": Object.freeze({ file: "Eligibility_Rules.csv", columns: Object.freeze(["Rule_ID", "Item_Type", "Required_Keywords", "Any_Keywords", "Excluded_Keywords"]) }),' 
if old_header not in text:
    raise SystemExit('Universal CSV header contract anchor missing')
text = text.replace(old_header, new_header, 1)

# Preserve category rules through normalization and cache flows.
normalize_anchor = '      data.tagDefinitions = Array.isArray(data.tagDefinitions) ? data.tagDefinitions : [];'
normalize_insert = '''      data.tagDefinitions = Array.isArray(data.tagDefinitions) ? data.tagDefinitions : [];
      data.eligibilityRules = (Array.isArray(data.eligibilityRules) ? data.eligibilityRules : []).map(rule => ({
        ruleId: cleanImportedText(rule && (rule.ruleId ?? rule.Rule_ID) || ""),
        itemType: cleanImportedText(rule && (rule.itemType ?? rule.Item_Type) || "").toUpperCase(),
        requiredKeywords: cleanImportedText(rule && (rule.requiredKeywords ?? rule.Required_Keywords) || ""),
        anyKeywords: cleanImportedText(rule && (rule.anyKeywords ?? rule.Any_Keywords) || ""),
        excludedKeywords: cleanImportedText(rule && (rule.excludedKeywords ?? rule.Excluded_Keywords) || "")
      })).filter(rule => rule.ruleId && rule.itemType);'''
if normalize_anchor not in text:
    raise SystemExit('normalizeData tagDefinitions anchor missing')
text = text.replace(normalize_anchor, normalize_insert, 1)

# Import the new Universal rule file.
tag_rows = '      const tagDefinitionRows = sheetToObjects(workbookSheets.Tag_Definitions || [], { sheetName: "Tag_Definitions", retainSourceRows: true });'
elig_rows = tag_rows + '\n      const eligibilityRuleRows = sheetToObjects(workbookSheets.Eligibility_Rules || [], { sheetName: "Eligibility_Rules", retainSourceRows: true });'
if tag_rows not in text:
    raise SystemExit('Universal tagDefinitionRows anchor missing')
text = text.replace(tag_rows, elig_rows, 1)

tag_map = '      data.tagDefinitions = mapImportedTagDefinitions(tagDefinitionRows);'
elig_map = '''      data.tagDefinitions = mapImportedTagDefinitions(tagDefinitionRows);
      data.eligibilityRules = eligibilityRuleRows.map(row => ({
        ruleId: cleanImportedText(getImportValue(row, "Rule_ID")),
        itemType: cleanImportedText(getImportValue(row, "Item_Type")).toUpperCase(),
        requiredKeywords: cleanImportedText(getImportValue(row, "Required_Keywords")),
        anyKeywords: cleanImportedText(getImportValue(row, "Any_Keywords")),
        excludedKeywords: cleanImportedText(getImportValue(row, "Excluded_Keywords"))
      })).filter(rule => rule.ruleId && rule.itemType);'''
if tag_map not in text:
    raise SystemExit('Universal tagDefinitions mapping anchor missing')
text = text.replace(tag_map, elig_map, 1)

old_required_check = '      if ((!data.abilities.length && !coreStratagemCount) || !data.tagDefinitions.length) {'
new_required_check = '      if ((!data.abilities.length && !coreStratagemCount) || !data.tagDefinitions.length || !data.eligibilityRules.length) {'
if old_required_check not in text:
    raise SystemExit('Universal required-data check anchor missing')
text = text.replace(old_required_check, new_required_check, 1)
text = text.replace(
    'Universal GitHub CSVs loaded, but required Abilities/Core Stratagems or Tag Definitions were not recognized.',
    'Universal GitHub CSVs loaded, but required Abilities/Core Stratagems, Tag Definitions, or Eligibility Rules were not recognized.',
    1
)

# Refresh the new rules alongside other Universal authoritative sheets.
text = text.replace('forceSheetNames: ["Abilities", "Tag_Definitions"]', 'forceSheetNames: ["Abilities", "Tag_Definitions", "Eligibility_Rules"]')

# Ensure empty/cached Universal data keeps eligibilityRules.
text = text.replace(
    'normalizeData({ units: [], weapons: [], abilities: [], detachments: [], tagDefinitions: [] })',
    'normalizeData({ units: [], weapons: [], abilities: [], detachments: [], tagDefinitions: [], eligibilityRules: [] })'
)
for source_name in ('cachedUniversalAbilityData', 'cachedUniversal', 'imported', 'cachedAfterFailure'):
    old = f'tagDefinitions: {source_name}.tagDefinitions || []'
    new = f'tagDefinitions: {source_name}.tagDefinitions || [], eligibilityRules: {source_name}.eligibilityRules || []'
    text = text.replace(old, new)

# Generic category + item keyword matcher. No keyword/category-specific rule is embedded here.
matcher_pattern = re.compile(
    r'    function detachmentItemMatchesUnitKeywords\(item, entry, unit, roster\) \{.*?\n    \}\n\n    function renderViewEditRosterAddPanel',
    re.S
)
match = matcher_pattern.search(text)
if not match:
    raise SystemExit('detachmentItemMatchesUnitKeywords block missing')
matcher = r'''    function getUniversalEligibilityRules() {
      return universalAbilityData && Array.isArray(universalAbilityData.eligibilityRules)
        ? universalAbilityData.eligibilityRules
        : [];
    }

    function eligibilityValuesMatchUnitKeywords(requiredValue, anyValue, excludedValue, unitKeywords) {
      const required = parseEligibilityKeywordList(requiredValue);
      const any = parseEligibilityKeywordList(anyValue);
      const excluded = parseEligibilityKeywordList(excludedValue);
      if (!required.every(keyword => unitKeywords.has(keyword))) return false;
      if (any.length && !any.some(keyword => unitKeywords.has(keyword))) return false;
      if (excluded.some(keyword => unitKeywords.has(keyword))) return false;
      return true;
    }

    function detachmentItemMatchesUnitKeywords(item, entry, unit, roster) {
      if (!item || !entry || !unit) return false;
      const effective = getEffectiveUnitProfile(entry, unit, roster);
      const unitKeywords = new Set((effective && Array.isArray(effective.keywords) ? effective.keywords : getKeywordsForUnit(unit)).map(normalizeEligibilityKeyword).filter(Boolean));
      const sourceConfig = getDataSourceConfig(activeArmyKey);
      const factionKeyword = normalizeEligibilityKeyword(sourceConfig && sourceConfig.factionKeyword);
      if (factionKeyword) unitKeywords.add(factionKeyword);

      const itemType = normalizeEligibilityKeyword(item.itemType || item.Item_Type || "");
      const categoryRules = itemType
        ? getUniversalEligibilityRules().filter(rule => normalizeEligibilityKeyword(rule && rule.itemType) === itemType)
        : [];
      if (categoryRules.some(rule => !eligibilityValuesMatchUnitKeywords(rule.requiredKeywords, rule.anyKeywords, rule.excludedKeywords, unitKeywords))) return false;

      return eligibilityValuesMatchUnitKeywords(
        getDetachmentItemEligibilityValue(item, "Required_Keywords"),
        getDetachmentItemEligibilityValue(item, "Any_Keywords"),
        getDetachmentItemEligibilityValue(item, "Excluded_Keywords"),
        unitKeywords
      );
    }

    function renderViewEditRosterAddPanel'''
text = text[:match.start()] + matcher + text[match.end():]

# In Edit, a Unit with zero legal Enhancements does not open the Enhancement panel.
old_toggle = '''      toggleViewEditRosterAddPanel(entryId) {
        if (!entryId) return;
        viewEditExpandedUnitRows[entryId] = true;
        const sections = getViewEditEntrySections(entryId);
        sections.add = !sections.add;
        RosterRender.refreshViewEditRosterDom();
      },'''
new_toggle = '''      toggleViewEditRosterAddPanel(entryId) {
        if (!entryId) return;
        viewEditExpandedUnitRows[entryId] = true;
        const sections = getViewEditEntrySections(entryId);
        if (appEditMode && !sections.add) {
          const roster = getViewEditRoster();
          const entry = getRosterEntryById(roster, entryId);
          const hasCurrentEnhancement = Boolean(entry && hasRosterEntryEnhancement(entry));
          const hasEligibleEnhancement = Boolean(roster && getAvailableEnhancementOptionsForRosterEntry(roster, entryId).length);
          if (!hasCurrentEnhancement && !hasEligibleEnhancement) {
            sections.add = false;
            RosterRender.refreshViewEditEntryExpandedState(entryId);
            return;
          }
        }
        sections.add = !sections.add;
        RosterRender.refreshViewEditRosterDom();
      },'''
if old_toggle not in text:
    raise SystemExit('Edit + toggle block missing')
text = text.replace(old_toggle, new_toggle, 1)

# Release note and rolling five detailed notes.
note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.6
    Scope: Adds Universal Eligibility_Rules.csv as the data-driven category eligibility layer. Category rules and item-level Required/Any/Excluded keyword rules now pass through the same generic matcher. ENHANCEMENT and UPGRADE category data exclude EPIC HERO without embedding EPIC HERO logic in HTML. Edit + does not open an Enhancement panel when the current Unit has no legal Enhancement choices.
    Risk areas: Universal reference loading/cache, generic eligibility matching, and Edit + availability. View Stratagem behavior and existing Enhancement selection behavior for legal Units are unchanged.
  -->

'''
insert_anchor = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.5'
if insert_anchor not in text:
    raise SystemExit('V31.5 note anchor missing')
text = text.replace(insert_anchor, note + insert_anchor, 1)
notes = list(re.finditer(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V[^\n]+\n.*?\n  -->\n', text, re.S))
if len(notes) > 5:
    for old_note in reversed(notes[5:]):
        text = text[:old_note.start()] + '\n' + text[old_note.end():]

# Add the authoritative Universal category-rule CSV and its schema contract.
rules_path.write_text(
    'Rule_ID,Item_Type,Required_Keywords,Any_Keywords,Excluded_Keywords\n'
    'global_enhancement_eligibility,ENHANCEMENT,,,EPIC HERO\n'
    'global_upgrade_eligibility,UPGRADE,,,EPIC HERO\n',
    encoding='utf-8'
)

schema_text = schema_path.read_text(encoding='utf-8')
if 'universal,Eligibility_Rules.csv,' not in schema_text:
    rows = [
        ['universal', 'Eligibility_Rules.csv', '1', 'Rule_ID', 'YES', 'AUTHORITATIVE', 'Stable global eligibility rule key.'],
        ['universal', 'Eligibility_Rules.csv', '2', 'Item_Type', 'YES', 'AUTHORITATIVE', 'Target item category; matched generically against item type.'],
        ['universal', 'Eligibility_Rules.csv', '3', 'Required_Keywords', 'NO', 'AUTHORITATIVE', 'All listed Unit keywords are required.'],
        ['universal', 'Eligibility_Rules.csv', '4', 'Any_Keywords', 'NO', 'AUTHORITATIVE', 'At least one listed Unit keyword is required when populated.'],
        ['universal', 'Eligibility_Rules.csv', '5', 'Excluded_Keywords', 'NO', 'AUTHORITATIVE', 'Any listed Unit keyword makes the item category ineligible.'],
    ]
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator='\n')
    writer.writerows(rows)
    if not schema_text.endswith('\n'):
        schema_text += '\n'
    schema_path.write_text(schema_text + buf.getvalue(), encoding='utf-8')

html_path.write_text(text, encoding='utf-8')

# Focused static validation.
check = html_path.read_text(encoding='utf-8')
assert '<title>WH40k 11th V31.6</title>' in check
assert check.count('const APP_VERSION = "31.6";') == 1
assert "version: 'V31.6'," in check
assert check.count('CHANGE NOTE - WH40k_11th_') == 5
assert 'Eligibility_Rules.csv' in check
assert 'function getUniversalEligibilityRules()' in check
assert 'categoryRules.some' in check
assert 'getAvailableEnhancementOptionsForRosterEntry(roster, entryId).length' in check
assert 'EPIC HERO' not in matcher

runtime = re.search(r'<script id="wh40k-runtime" type="text/wh40k-runtime">(.*?)</script>', check, re.S)
if not runtime:
    raise SystemExit('runtime script not found')
Path('/tmp/wh40k-runtime.js').write_text(runtime.group(1), encoding='utf-8')
subprocess.run(['node', '--check', '/tmp/wh40k-runtime.js'], check=True)
print('V31.6 category eligibility patch checks passed')
