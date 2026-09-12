from pathlib import Path
import csv
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


replace_once('<title>WH40k 11th V31.1</title>', '<title>WH40k 11th V31.2</title>', 'title')
replace_once('const APP_VERSION = "31.1";', 'const APP_VERSION = "31.2";', 'APP_VERSION')
replace_once("version: 'V31.1',", "version: 'V31.2',", 'InternalQuality version')
replace_once('current baseline is WH40k_11th_V31.1', 'current baseline is WH40k_11th_V31.2', 'maintenance baseline')

width_old = 'repeat(4, minmax(0, 1fr)) minmax(0, .333fr)'
if text.count(width_old) != 2:
    raise SystemExit(f'+ width: expected 2 grid matches, found {text.count(width_old)}')
text = text.replace(width_old, 'repeat(4, minmax(0, 1fr)) minmax(0, .666fr)')

css_anchor = '''    .category-add-button {
      width: 100%;
      min-width: 0;
      height: auto;
      min-height: 0;
      padding: 9px 0;
      font-size: var(--font-name);
      line-height: 1;
      align-self: stretch;
    }
'''
css_new = css_anchor + '''
    .category-add-button.active {
      background: var(--color-bg-button-active);
    }

    .view-edit-unit-add-panel {
      padding: 0 8px 8px;
      background: var(--edit-roster-row-bg);
    }

    .view-edit-unit-add-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
    }

    .view-edit-unit-add-option {
      min-width: 0;
      height: auto;
      padding: 9px 4px;
      line-height: 1.15;
      white-space: normal;
      overflow-wrap: anywhere;
    }

    .view-edit-unit-add-empty {
      padding: 9px 4px;
      color: var(--text-muted);
      font-size: var(--font-meta);
    }
'''
replace_once(css_anchor, css_new, 'add panel CSS')

helper_anchor = '''    function getViewEditEntrySections(entryId) {
      if (!viewEditOpenEntrySections[entryId]) {
        viewEditOpenEntrySections[entryId] = {};
      }
      return viewEditOpenEntrySections[entryId];
    }
'''
helper_new = helper_anchor + r'''

    function normalizeEligibilityKeyword(value) {
      return String(value || "").trim().replace(/\s+/g, " ").toUpperCase();
    }

    function parseEligibilityKeywordList(value) {
      return String(value || "").split(",").map(normalizeEligibilityKeyword).filter(Boolean);
    }

    function getDetachmentItemEligibilityValue(item, columnName) {
      if (!item) return "";
      const directNames = {
        Required_Keywords: ["requiredKeywords", "Required_Keywords"],
        Any_Keywords: ["anyKeywords", "Any_Keywords"],
        Excluded_Keywords: ["excludedKeywords", "Excluded_Keywords"]
      };
      for (const key of directNames[columnName] || []) {
        const value = String(item[key] ?? "").trim();
        if (value) return value;
      }
      const source = normalizeSpreadsheetSourceRowRecord(item.spreadsheetEditSource);
      if (!source) return "";
      const index = getSpreadsheetSourceColumnIndex(source, columnName);
      return index >= 0 && Array.isArray(source.row) ? String(source.row[index] ?? "").trim() : "";
    }

    function detachmentItemMatchesUnitKeywords(item, entry, unit, roster) {
      if (!item || !entry || !unit) return false;
      const effective = getEffectiveUnitProfile(entry, unit, roster);
      const unitKeywords = new Set((effective && Array.isArray(effective.keywords) ? effective.keywords : getKeywordsForUnit(unit)).map(normalizeEligibilityKeyword).filter(Boolean));
      const required = parseEligibilityKeywordList(getDetachmentItemEligibilityValue(item, "Required_Keywords"));
      const any = parseEligibilityKeywordList(getDetachmentItemEligibilityValue(item, "Any_Keywords"));
      const excluded = parseEligibilityKeywordList(getDetachmentItemEligibilityValue(item, "Excluded_Keywords"));
      if (!required.every(keyword => unitKeywords.has(keyword))) return false;
      if (any.length && !any.some(keyword => unitKeywords.has(keyword))) return false;
      if (excluded.some(keyword => unitKeywords.has(keyword))) return false;
      return true;
    }

    function renderViewEditRosterAddPanel(entry, unit) {
      const roster = getViewEditRoster();
      if (!entry || !unit || !roster) return "";

      if (appEditMode) {
        const selectedItem = getRosterEntryEnhancementItem(entry, roster);
        const selectedId = String((selectedItem && selectedItem.itemId) || entry.enhancementItemId || "").trim();
        let items = getAvailableEnhancementOptionsForRosterEntry(roster, entry.entryId)
          .filter(item => detachmentItemMatchesUnitKeywords(item, entry, unit, roster));
        if (selectedItem && !items.some(item => String(item.itemId || "").trim() === String(selectedItem.itemId || "").trim())) {
          items = [selectedItem, ...items];
        }
        if (!items.length) return `<div class="view-edit-unit-add-panel"><div class="view-edit-unit-add-empty">No eligible Enhancements.</div></div>`;
        return `<div class="view-edit-unit-add-panel"><div class="view-edit-unit-add-grid">${items.map(item => {
          const itemId = String(item.itemId || "").trim();
          const selected = Boolean(selectedId && itemId === selectedId);
          const points = cleanImportedText(item.points ?? "");
          const label = `${item.itemName || itemId || "Enhancement"}${points ? ` · ${points} pts` : ""}`;
          const nextValue = selected ? "" : itemId;
          return `<button type="button" class="category-button view-edit-unit-add-option${selected ? " active" : ""}" onclick="event.stopPropagation(); RosterActions.updateViewEditRosterEntryEnhancementSelection('${UI.escapeJs(entry.entryId)}', '${UI.escapeJs(nextValue)}')">${escapeHtml(label)}</button>`;
        }).join("")}</div></div>`;
      }

      const selectedKeys = new Set(getRosterEntryUnitStratagemKeys(entry));
      const items = getRosterUnitSelectableStratagems(roster)
        .filter(item => detachmentItemMatchesUnitKeywords(item, entry, unit, roster));
      if (!items.length) return `<div class="view-edit-unit-add-panel"><div class="view-edit-unit-add-empty">No eligible Stratagems.</div></div>`;
      return `<div class="view-edit-unit-add-panel"><div class="view-edit-unit-add-grid">${items.map(item => {
        const itemKey = getDetachmentStratagemItemEditKey(item);
        const selected = selectedKeys.has(itemKey);
        const cp = cleanImportedText(item.cpCost ?? "");
        const label = `${item.itemName || item.itemId || "Stratagem"}${cp ? ` · ${cp}CP` : ""}`;
        return `<button type="button" class="category-button view-edit-unit-add-option${selected ? " active" : ""}" onclick="event.stopPropagation(); RosterActions.toggleViewEditRosterEntryStratagemSelection('${UI.escapeJs(entry.entryId)}', '${UI.escapeJs(itemKey)}')">${escapeHtml(label)}</button>`;
      }).join("")}</div></div>`;
    }
'''
replace_once(helper_anchor, helper_new, 'keyword helper insertion')

replace_once(
    '      const keywordsOpen = Boolean(sections.keywords);\n      const unitEditKey = getUnitItemEditKey(unit);',
    '      const keywordsOpen = Boolean(sections.keywords);\n      const addOpen = Boolean(sections.add);\n      const unitEditKey = getUnitItemEditKey(unit);',
    'add panel state'
)

tabs_old = '''              <button class="category-button ${keywordsOpen ? "active" : ""}" data-entry-section-button="keywords" onclick="event.stopPropagation(); RosterActions.toggleViewEditRosterSection('${UI.escapeJs(entry.entryId)}', 'keywords')">Keywords</button>
              <button class="category-add-button" type="button" aria-label="Add" onclick="event.stopPropagation()">+</button>
            </div>

            <div class="selected-entry-detail-section ${statsOpen ? "active" : ""}" data-entry-section="stats">'''
tabs_new = '''              <button class="category-button ${keywordsOpen ? "active" : ""}" data-entry-section-button="keywords" onclick="event.stopPropagation(); RosterActions.toggleViewEditRosterSection('${UI.escapeJs(entry.entryId)}', 'keywords')">Keywords</button>
              <button class="category-add-button${addOpen ? " active" : ""}" type="button" aria-label="Add" aria-expanded="${addOpen}" onclick="event.stopPropagation(); RosterActions.toggleViewEditRosterAddPanel('${UI.escapeJs(entry.entryId)}')">+</button>
            </div>
            ${addOpen ? renderViewEditRosterAddPanel(entry, unit) : ""}

            <div class="selected-entry-detail-section ${statsOpen ? "active" : ""}" data-entry-section="stats">'''
replace_once(tabs_old, tabs_new, 'add panel render')

action_anchor = '''      toggleViewEditRosterSection(entryId, section) {
        viewEditExpandedUnitRows[entryId] = true;
        const sections = getViewEditEntrySections(entryId);
        sections[section] = !sections[section];
        RosterRender.refreshViewEditEntryExpandedState(entryId);
      },
      updateViewEditRosterEntryEnhancementSelection(entryId, itemId) {'''
action_new = '''      toggleViewEditRosterSection(entryId, section) {
        viewEditExpandedUnitRows[entryId] = true;
        const sections = getViewEditEntrySections(entryId);
        sections[section] = !sections[section];
        RosterRender.refreshViewEditEntryExpandedState(entryId);
      },
      toggleViewEditRosterAddPanel(entryId) {
        if (!entryId) return;
        viewEditExpandedUnitRows[entryId] = true;
        const sections = getViewEditEntrySections(entryId);
        sections.add = !sections.add;
        RosterRender.refreshViewEditEntryExpandedState(entryId);
      },
      toggleViewEditRosterEntryStratagemSelection(entryId, stratagemKey) {
        if (appEditMode || !entryId || !stratagemKey) return;
        const roster = getViewEditRoster();
        const entry = getRosterEntryById(roster, entryId);
        const unit = entry ? getUnitById(entry.unitId) : null;
        if (!entry || !unit || isSpacerEntry(entry) || isRosterEntryPendingDeletion(entry)) return;
        const cleanKey = String(stratagemKey || "").trim();
        let keys = getRosterEntryUnitStratagemKeys(entry);
        if (keys.includes(cleanKey)) {
          keys = keys.filter(key => key !== cleanKey);
        } else {
          const candidate = getRosterUnitSelectableStratagems(roster).find(item => getDetachmentStratagemItemEditKey(item) === cleanKey);
          if (!candidate || !detachmentItemMatchesUnitKeywords(candidate, entry, unit, roster)) return;
          keys = [...keys, cleanKey];
        }
        entry.unitStratagemKeys = keys;
        entry.unitStratagemKey = keys[0] || "";
        synchronizeRosterUnitAbilityCollections(entry);
        rosterWorkingStateDirty = true;
        invalidateRosterModeDomCache("edit");
        scheduleRosterModeDomCacheBuild("edit");
        RosterRender.refreshViewEditRosterDom();
      },
      updateViewEditRosterEntryEnhancementSelection(entryId, itemId) {'''
replace_once(action_anchor, action_new, 'RosterActions add-panel actions')

note_anchor = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.1'''
note_new = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.2
    Scope: The Unit detail + control is two-thirds of a normal category tab and opens a keyword-matched add panel. Edit shows eligible selected-Detachment Enhancements and reuses the existing max-one paid Enhancement path; View shows eligible selected-Detachment Stratagems with multi-select add/remove. Eligibility uses Required_Keywords, Any_Keywords, and Excluded_Keywords against the Unit effective Keywords, with all keywords treated identically.
    Risk areas: Unit detail rendering, normalized spreadsheet-source metadata, and roster Stratagem/Enhancement state. Existing Tags/Probable mechanics and unrelated Detachment reference/edit surfaces are unchanged.
  -->

  <!--
    CHANGE NOTE - WH40k_11th_V31.1'''
replace_once(note_anchor, note_new, 'V31.2 release note')

old_note_pattern = re.compile(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V30\.6\n.*?\n  -->\n', re.S)
text, removed = old_note_pattern.subn('\n', text, count=1)
if removed != 1:
    raise SystemExit(f'old release note: expected 1 V30.6 note, removed {removed}')

path.write_text(text, encoding='utf-8')

# Static checks.
text = path.read_text(encoding='utf-8')
assert '<title>WH40k 11th V31.2</title>' in text
assert text.count('const APP_VERSION = "31.2";') == 1
assert "version: 'V31.2'," in text
assert text.count('CHANGE NOTE - WH40k_11th_') == 5
assert 'minmax(0, .666fr)' in text
for marker in ('Required_Keywords', 'Any_Keywords', 'Excluded_Keywords', 'renderViewEditRosterAddPanel', 'toggleViewEditRosterEntryStratagemSelection'):
    assert marker in text, marker

# BOYZ + War Horde data acceptance.
with open('data/orks/Unit_Profiles.csv', newline='', encoding='utf-8') as f:
    units = list(csv.DictReader(f))
boyz = next(row for row in units if str(row.get('Unit Name', '')).strip().upper() == 'BOYZ')
unit_keywords = {x.strip().upper() for x in str(boyz.get('Keywords', '')).split(',') if x.strip()}


def matches(row):
    req = {x.strip().upper() for x in str(row.get('Required_Keywords', '')).split(',') if x.strip()}
    any_kw = {x.strip().upper() for x in str(row.get('Any_Keywords', '')).split(',') if x.strip()}
    exc = {x.strip().upper() for x in str(row.get('Excluded_Keywords', '')).split(',') if x.strip()}
    return req.issubset(unit_keywords) and (not any_kw or bool(any_kw & unit_keywords)) and not bool(exc & unit_keywords)


with open('data/orks/Enhancements.csv', newline='', encoding='utf-8') as f:
    enhancements = [r for r in csv.DictReader(f) if r.get('Detachment_ID') == 'orks_war_horde']
assert len(enhancements) == 4 and all(matches(r) for r in enhancements)

with open('data/orks/Stratagems.csv', newline='', encoding='utf-8') as f:
    stratagems = [r for r in csv.DictReader(f) if r.get('Detachment_ID') == 'orks_war_horde']
eligible = {r['Stratagem_Name'] for r in stratagems if matches(r)}
assert {"BREAKIN' HEADS", "HIT 'EM HARDER", 'ORKS IS NEVER BEATEN', 'CLOSE-RANGE DAKKA'}.issubset(eligible)
assert "MOW 'EM DOWN" not in eligible
assert 'FUNGUS-FUEL INJECTION' not in eligible

runtime = re.search(r'<script id="wh40k-runtime" type="text/wh40k-runtime">(.*?)</script>', text, re.S)
if not runtime:
    raise SystemExit('runtime script not found')
Path('/tmp/wh40k-runtime.js').write_text(runtime.group(1), encoding='utf-8')
subprocess.run(['node', '--check', '/tmp/wh40k-runtime.js'], check=True)
print('V31.2 static and BOYZ War Horde acceptance checks passed')
