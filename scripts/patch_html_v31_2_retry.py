from pathlib import Path

source_path = Path('scripts/patch_html_v31_2.py')
source = source_path.read_text(encoding='utf-8')
start = source.index("action_anchor = '''")
marker = "replace_once(action_anchor, action_new, 'RosterActions add-panel actions')"
end = source.index(marker, start) + len(marker)

replacement = r'''action_anchor = '''\''      updateViewEditRosterEntryEnhancementSelection(entryId, itemId) {'''\''
action_new = '''\''      toggleViewEditRosterAddPanel(entryId) {
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
      updateViewEditRosterEntryEnhancementSelection(entryId, itemId) {'''\''
replace_once(action_anchor, action_new, 'RosterActions add-panel actions')'''

patched = source[:start] + replacement + source[end:]
exec(compile(patched, str(source_path), 'exec'), {'__name__': '__main__'})
