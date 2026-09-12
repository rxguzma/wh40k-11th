from pathlib import Path
import re, subprocess

path = Path('WH40k_11th.html')
text = path.read_text(encoding='utf-8')

# Version.
text = text.replace('<title>WH40k 11th V31.4</title>', '<title>WH40k 11th V31.5</title>', 1)
text = text.replace('current baseline is WH40k_11th_V31.4;', 'current baseline is WH40k_11th_V31.5;', 1)
text = text.replace('const APP_VERSION = "31.4";', 'const APP_VERSION = "31.5";', 1)
text = text.replace("version: 'V31.4',", "version: 'V31.5',", 1)

# Normal View needs to render selected Unit Stratagems inside Abilities.
view_render_anchor = '    function renderRosterUnitDetailPanel(entry, unit, index) {'
if view_render_anchor not in text:
    raise SystemExit('renderRosterUnitDetailPanel anchor missing')

helpers = r'''    function renderRosterViewAbilitiesBox(entry, unit) {
      const roster = getActiveRoster();
      const baseHtml = renderUnitAbilityBoxes(unit, entry, false);
      const stratagemRows = renderUnitAbilityStratagemDisplayRows(entry, roster, 0);
      if (!stratagemRows) return baseHtml;
      return baseHtml.replace('</tbody>', `${stratagemRows}</tbody>`);
    }

    function refreshRosterViewAbilitiesPanel(entryId) {
      const roster = getActiveRoster();
      if (!roster || !entryId || !Array.isArray(roster.entries)) return false;
      const index = roster.entries.findIndex(item => item && item.entryId === entryId);
      if (index < 0) return false;
      const entry = roster.entries[index];
      const unit = entry ? getUnitById(entry.unitId) : null;
      const panel = document.getElementById(`abilities-${index}`);
      if (!entry || !unit || !panel) return false;
      panel.innerHTML = renderRosterViewAbilitiesBox(entry, unit);
      return true;
    }

'''
if 'function renderRosterViewAbilitiesBox(entry, unit)' not in text:
    text = text.replace(view_render_anchor, helpers + view_render_anchor, 1)

old_call = '${renderUnitAbilityBoxes(unit, entry, false)}'
new_call = '${renderRosterViewAbilitiesBox(entry, unit)}'
if old_call not in text:
    raise SystemExit('normal View abilities call missing')
text = text.replace(old_call, new_call, 1)

# When a View Stratagem is selected/unselected, repaint both the + choices and Abilities immediately.
action_anchor = '        refreshRosterViewAddPanel(entryId);\n      },\n      updateViewEditRosterEntryEnhancementSelection'
replacement = '        refreshRosterViewAddPanel(entryId);\n        refreshRosterViewAbilitiesPanel(entryId);\n      },\n      updateViewEditRosterEntryEnhancementSelection'
if action_anchor not in text:
    raise SystemExit('View stratagem action refresh anchor missing')
text = text.replace(action_anchor, replacement, 1)

# Release note and rolling five detailed notes.
note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.5
    Scope: Normal View + Stratagem selection now behaves like the existing Unit Ability workflow: selected Stratagems are rendered immediately inside the Unit Abilities table and are removed from Abilities when deselected. The + panel still owns eligibility and green selected state; Edit Enhancement behavior is unchanged.
    Risk areas: Normal View Unit Abilities rendering and View Stratagem selection refresh only. Edit mode, Tags/Probable, and unrelated roster behavior are unchanged.
  -->

'''
insert_anchor = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.4'
if insert_anchor not in text:
    raise SystemExit('V31.4 note anchor missing')
text = text.replace(insert_anchor, note + insert_anchor, 1)
notes = list(re.finditer(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V[^\n]+\n.*?\n  -->\n', text, re.S))
if len(notes) > 5:
    for match in reversed(notes[5:]):
        text = text[:match.start()] + '\n' + text[match.end():]

path.write_text(text, encoding='utf-8')

# Focused static checks.
text = path.read_text(encoding='utf-8')
assert '<title>WH40k 11th V31.5</title>' in text
assert text.count('const APP_VERSION = "31.5";') == 1
assert "version: 'V31.5'," in text
assert text.count('CHANGE NOTE - WH40k_11th_') == 5
assert 'function renderRosterViewAbilitiesBox(entry, unit)' in text
assert 'renderUnitAbilityStratagemDisplayRows(entry, roster, 0)' in text
assert '${renderRosterViewAbilitiesBox(entry, unit)}' in text
assert 'refreshRosterViewAbilitiesPanel(entryId);' in text

runtime = re.search(r'<script id="wh40k-runtime" type="text/wh40k-runtime">(.*?)</script>', text, re.S)
if not runtime:
    raise SystemExit('runtime script not found')
Path('/tmp/wh40k-runtime.js').write_text(runtime.group(1), encoding='utf-8')
subprocess.run(['node', '--check', '/tmp/wh40k-runtime.js'], check=True)
print('V31.5 View Stratagem-to-Abilities checks passed')
