from pathlib import Path
import re

path = Path("WH40k_11th.html")
text = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    text = text.replace(old, new, 1)


def replace_count(old: str, new: str, expected: int, label: str) -> None:
    global text
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"{label}: expected {expected} matches, found {count}")
    text = text.replace(old, new)


# Sequential release metadata.
replace_once('<title>WH40k 11th V31.8</title>', '<title>WH40k 11th V31.9</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.8;', 'The current baseline is WH40k_11th_V31.9;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.8";', 'const APP_VERSION = "31.9";', 'APP_VERSION')
replace_once("version: 'V31.8',", "version: 'V31.9',", 'InternalQuality version')

note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.8\n"
if note_marker not in text:
    raise SystemExit("release note insertion marker missing")
new_note = """  <!--
    CHANGE NOTE - WH40k_11th_V31.9
    Scope: Remove the noticeable delay when opening Unit + panels for Enhancements or Stratagems. Eligibility now computes the Unit's effective keyword set once per panel render and reuses it for every candidate item instead of rebuilding the effective Unit profile once per candidate. Eligibility results and data-driven rules are unchanged.
    Risk areas: Unit + panel eligibility filtering and performance only. Enhancement/Stratagem selection semantics, keyword rules, and unrelated roster rendering remain unchanged.
  -->

"""
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.4\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f"old release note removal: expected 1 match, found {removed}")

old_matcher = """    function detachmentItemMatchesUnitKeywords(item, entry, unit, roster) {
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
"""
new_matcher = """    function getUnitEligibilityKeywordSet(entry, unit, roster) {
      if (!entry || !unit) return new Set();
      const effective = getEffectiveUnitProfile(entry, unit, roster);
      const unitKeywords = new Set((effective && Array.isArray(effective.keywords) ? effective.keywords : getKeywordsForUnit(unit)).map(normalizeEligibilityKeyword).filter(Boolean));
      const sourceConfig = getDataSourceConfig(activeArmyKey);
      const factionKeyword = normalizeEligibilityKeyword(sourceConfig && sourceConfig.factionKeyword);
      if (factionKeyword) unitKeywords.add(factionKeyword);
      return unitKeywords;
    }

    function detachmentItemMatchesUnitKeywords(item, entry, unit, roster, precomputedUnitKeywords = null) {
      if (!item || !entry || !unit) return false;
      const unitKeywords = precomputedUnitKeywords instanceof Set
        ? precomputedUnitKeywords
        : getUnitEligibilityKeywordSet(entry, unit, roster);

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
"""
replace_once(old_matcher, new_matcher, "eligibility matcher optimization")

replace_once(
    """    function renderViewEditRosterAddPanel(entry, unit) {
      const roster = getViewEditRoster();
      if (!entry || !unit || !roster) return "";

      if (appEditMode) {
""",
    """    function renderViewEditRosterAddPanel(entry, unit) {
      const roster = getViewEditRoster();
      if (!entry || !unit || !roster) return "";
      const unitKeywords = getUnitEligibilityKeywordSet(entry, unit, roster);

      if (appEditMode) {
""",
    "View/Edit add-panel keyword context",
)

replace_once(
    """    function renderRosterViewAddPanel(entry, unit) {
      const roster = getActiveRoster();
      if (!entry || !unit || !roster) return "";
      const selectedKeys = new Set(getRosterEntryUnitStratagemKeys(entry));
""",
    """    function renderRosterViewAddPanel(entry, unit) {
      const roster = getActiveRoster();
      if (!entry || !unit || !roster) return "";
      const unitKeywords = getUnitEligibilityKeywordSet(entry, unit, roster);
      const selectedKeys = new Set(getRosterEntryUnitStratagemKeys(entry));
""",
    "View add-panel keyword context",
)

replace_count(
    ".filter(item => detachmentItemMatchesUnitKeywords(item, entry, unit, roster));",
    ".filter(item => detachmentItemMatchesUnitKeywords(item, entry, unit, roster, unitKeywords));",
    3,
    "add-panel eligibility filters",
)

checks = [
    '<title>WH40k 11th V31.9</title>',
    'const APP_VERSION = "31.9";',
    "version: 'V31.9',",
    'function getUnitEligibilityKeywordSet(entry, unit, roster)',
    'precomputedUnitKeywords instanceof Set',
    'const unitKeywords = getUnitEligibilityKeywordSet(entry, unit, roster);'
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))
if text.count('detachmentItemMatchesUnitKeywords(item, entry, unit, roster, unitKeywords)') != 3:
    raise SystemExit('expected exactly three optimized add-panel eligibility filter calls')

path.write_text(text, encoding="utf-8")
print("Patched WH40k_11th.html to V31.9")
