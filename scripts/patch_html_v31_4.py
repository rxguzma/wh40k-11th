from pathlib import Path
import re, subprocess

path = Path('WH40k_11th.html')
text = path.read_text(encoding='utf-8')

# Version.
text = text.replace('<title>WH40k 11th V31.3</title>', '<title>WH40k 11th V31.4</title>', 1)
text = text.replace('current baseline is WH40k_11th_V31.3;', 'current baseline is WH40k_11th_V31.4;', 1)
text = text.replace('const APP_VERSION = "31.3";', 'const APP_VERSION = "31.4";', 1)
text = text.replace("version: 'V31.3',", "version: 'V31.4',", 1)

# Small, normal-weight text for the new choice boxes.
css_pattern = re.compile(r'(    \.view-edit-unit-add-option \{\n.*?)(    \}\n)', re.S)
m = css_pattern.search(text)
if not m:
    raise SystemExit('view-edit-unit-add-option CSS block not found')
block = m.group(1)
block = re.sub(r'\n      font-size: [^;]+;', '', block)
block = re.sub(r'\n      font-weight: [^;]+;', '', block)
block += '\n      font-size: 10px;\n      font-weight: 400;'
text = text[:m.start()] + block + '\n' + m.group(2) + text[m.end():]

# Dedicated normal-View Stratagem panel. Do not route normal View through the Edit draft.
helper_anchor = '    function renderViewEditRosterUnitDetails(entry, unit) {'
if helper_anchor not in text:
    raise SystemExit('renderViewEditRosterUnitDetails anchor missing')
view_helpers = r'''    function renderRosterViewAddPanel(entry, unit) {
      const roster = getActiveRoster();
      if (!entry || !unit || !roster) return "";
      const selectedKeys = new Set(getRosterEntryUnitStratagemKeys(entry));
      const items = getRosterUnitSelectableStratagems(roster)
        .filter(item => detachmentItemMatchesUnitKeywords(item, entry, unit, roster));
      if (!items.length) return `<div class="view-edit-unit-add-panel"><div class="view-edit-unit-add-empty">No eligible Stratagems.</div></div>`;
      return `<div class="view-edit-unit-add-panel"><div class="view-edit-unit-add-grid">${items.map(item => {
        const itemKey = getDetachmentStratagemItemEditKey(item);
        const selected = selectedKeys.has(itemKey);
        const cp = cleanImportedText(item.cpCost ?? "");
        const label = `${item.itemName || item.itemId || "Stratagem"}${cp ? ` · ${cp}CP` : ""}`;
        return `<button type="button" class="category-button view-edit-unit-add-option${selected ? " green" : ""}" onclick="event.stopPropagation(); RosterActions.toggleViewEditRosterEntryStratagemSelection('${UI.escapeJs(entry.entryId)}', '${UI.escapeJs(itemKey)}')">${escapeHtml(label)}</button>`;
      }).join("")}</div></div>`;
    }

    function refreshRosterViewAddPanel(entryId) {
      const roster = getActiveRoster();
      if (!roster || !entryId) return false;
      const index = Array.isArray(roster.entries) ? roster.entries.findIndex(item => item && item.entryId === entryId) : -1;
      if (index < 0) return false;
      const entry = roster.entries[index];
      const unit = entry ? getUnitById(entry.unitId) : null;
      const panel = document.getElementById(`add-${index}`);
      if (!entry || !unit || !panel) return false;
      panel.innerHTML = renderRosterViewAddPanel(entry, unit);
      return true;
    }

'''
if 'function renderRosterViewAddPanel(entry, unit)' in text:
    raise SystemExit('View add helper already exists')
text = text.replace(helper_anchor, view_helpers + helper_anchor, 1)

# Wire the real normal-View + button to the existing View section toggle system.
old_view_fn = '''    function renderRosterUnitDetailPanel(entry, unit, index) {
      const effectiveProfile = getEffectiveUnitProfile(entry, unit, getActiveRoster());
      return `<div class="category-tabs"><button class="category-button" id="btn-weapons-${index}" onclick="event.stopPropagation(); UI.toggleSection(${index}, 'weapons')">Weapons</button><button class="category-button" id="btn-abilities-${index}" onclick="event.stopPropagation(); UI.toggleSection(${index}, 'abilities')">Abilities</button><button class="category-button" id="btn-keywords-${index}" onclick="event.stopPropagation(); UI.toggleSection(${index}, 'keywords')">Keywords</button><button class="category-button" id="btn-probable-${index}" onclick="event.stopPropagation(); UI.toggleSection(${index}, 'probable')">Probable</button><button class="category-add-button" type="button" aria-label="Add" onclick="event.stopPropagation()">+</button></div><div class="subsection active-unit-detail-box" id="weapons-${index}">${renderWeapons(getWeaponsForRosterEntry(entry, unit), unit.unitId, false, entry)}</div><div class="subsection active-unit-detail-box" id="abilities-${index}">${renderUnitAbilityBoxes(unit, entry, false)}</div><div class="subsection active-unit-detail-box" id="keywords-${index}">${renderKeywords(effectiveProfile.keywords, unit.unitId, false, entry)}</div><div class="subsection active-unit-detail-box" id="probable-${index}">${renderProbablePanel(entry, unit)}</div>`;
    }
'''
new_view_fn = '''    function renderRosterUnitDetailPanel(entry, unit, index) {
      const effectiveProfile = getEffectiveUnitProfile(entry, unit, getActiveRoster());
      return `<div class="category-tabs"><button class="category-button" id="btn-weapons-${index}" onclick="event.stopPropagation(); UI.toggleSection(${index}, 'weapons')">Weapons</button><button class="category-button" id="btn-abilities-${index}" onclick="event.stopPropagation(); UI.toggleSection(${index}, 'abilities')">Abilities</button><button class="category-button" id="btn-keywords-${index}" onclick="event.stopPropagation(); UI.toggleSection(${index}, 'keywords')">Keywords</button><button class="category-button" id="btn-probable-${index}" onclick="event.stopPropagation(); UI.toggleSection(${index}, 'probable')">Probable</button><button class="category-add-button" id="btn-add-${index}" type="button" aria-label="Add" onclick="event.stopPropagation(); UI.toggleSection(${index}, 'add')">+</button></div><div class="subsection active-unit-detail-box" id="add-${index}">${renderRosterViewAddPanel(entry, unit)}</div><div class="subsection active-unit-detail-box" id="weapons-${index}">${renderWeapons(getWeaponsForRosterEntry(entry, unit), unit.unitId, false, entry)}</div><div class="subsection active-unit-detail-box" id="abilities-${index}">${renderUnitAbilityBoxes(unit, entry, false)}</div><div class="subsection active-unit-detail-box" id="keywords-${index}">${renderKeywords(effectiveProfile.keywords, unit.unitId, false, entry)}</div><div class="subsection active-unit-detail-box" id="probable-${index}">${renderProbablePanel(entry, unit)}</div>`;
    }
'''
if old_view_fn not in text:
    raise SystemExit('normal View renderRosterUnitDetailPanel exact block not found')
text = text.replace(old_view_fn, new_view_fn, 1)

# Normal View Stratagem selection must mutate the active roster and repaint only the open add panel.
action_pattern = re.compile(r'(      toggleViewEditRosterEntryStratagemSelection\(entryId, stratagemKey\) \{\n.*?\n      \},\n)(      updateViewEditRosterEntryEnhancementSelection)', re.S)
m = action_pattern.search(text)
if not m:
    raise SystemExit('Stratagem selection action block missing')
action = m.group(1)
if 'const roster = getViewEditRoster();' not in action:
    raise SystemExit('expected View action roster source missing')
action = action.replace('const roster = getViewEditRoster();', 'const roster = getActiveRoster();', 1)
if 'RosterRender.refreshViewEditRosterDom();' not in action:
    raise SystemExit('expected View action refresh missing')
action = action.replace('RosterRender.refreshViewEditRosterDom();', 'refreshRosterViewAddPanel(entryId);', 1)
text = text[:m.start()] + action + m.group(2) + text[m.end():]

# Release note and last-five maintenance.
note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.4
    Scope: Fix the actual normal-View + button so it opens keyword-matched Stratagems using the existing View subsection toggle path. View Stratagem clicks now mutate the active roster directly and repaint the open panel so selected choices immediately show success green. Add-panel choice typography is reduced to 10px normal weight.
    Risk areas: Normal View Unit detail + panel and its Stratagem selection state only. Edit Enhancements, Tags/Probable, and unrelated roster behavior are unchanged.
  -->

'''
insert_anchor = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.3'
if insert_anchor not in text:
    raise SystemExit('V31.3 note anchor missing')
text = text.replace(insert_anchor, note + insert_anchor, 1)
notes = list(re.finditer(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V[^\n]+\n.*?\n  -->\n', text, re.S))
if len(notes) > 5:
    for match in reversed(notes[5:]):
        text = text[:match.start()] + '\n' + text[match.end():]

path.write_text(text, encoding='utf-8')

# Focused static checks.
text = path.read_text(encoding='utf-8')
assert '<title>WH40k 11th V31.4</title>' in text
assert text.count('const APP_VERSION = "31.4";') == 1
assert "version: 'V31.4'," in text
assert text.count('CHANGE NOTE - WH40k_11th_') == 5
assert 'font-size: 10px;' in text and 'font-weight: 400;' in text
assert 'id="btn-add-${index}"' in text
assert "UI.toggleSection(${index}, 'add')" in text
assert 'id="add-${index}"' in text
assert 'renderRosterViewAddPanel(entry, unit)' in text
assert 'const roster = getActiveRoster();' in text
assert 'refreshRosterViewAddPanel(entryId);' in text
assert '<button class="category-add-button" type="button" aria-label="Add" onclick="event.stopPropagation()">+</button>' not in text

runtime = re.search(r'<script id="wh40k-runtime" type="text/wh40k-runtime">(.*?)</script>', text, re.S)
if not runtime:
    raise SystemExit('runtime script not found')
Path('/tmp/wh40k-runtime.js').write_text(runtime.group(1), encoding='utf-8')
subprocess.run(['node', '--check', '/tmp/wh40k-runtime.js'], check=True)
print('V31.4 View plus panel and typography checks passed')
