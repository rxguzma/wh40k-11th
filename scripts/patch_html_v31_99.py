from pathlib import Path
import re

path = Path('WH40k_11th.html')
text = path.read_text(encoding='utf-8')


def once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


# Sequential release metadata.
once('<title>WH40k 11th V31.98</title>', '<title>WH40k 11th V31.99</title>', 'title')
once('The current baseline is WH40k_11th_V31.98;', 'The current baseline is WH40k_11th_V31.99;', 'baseline')
once('const APP_VERSION = "31.98";', 'const APP_VERSION = "31.99";', 'APP_VERSION')
once("version: 'V31.98',", "version: 'V31.99',", 'quality version')

# Preserve the top-level New View route across a release switch. The stable
# version host lives in the parent window while release runtimes are replaced,
# so keep only the one-shot route marker there. Old View/Edit/Cards do not set
# the marker and therefore keep their existing startup behavior.
old_loader = '''    async function loadGithubVersion(version) {
      if (versionActionBusy || !canReloadAppVersion()) return false;
      const target = normalizeAppVersion(version);
      if (target === APP_VERSION) { setVersionHistoryStatus(`v${APP_VERSION} is running.`, "success", true); return true; }
      versionActionBusy = true;
      setVersionHistoryStatus(`Loading v${target}…`, "", true);
      try { return await getVersionHost().load(target); }
      catch (error) { setVersionHistoryStatus(error.message, "error", true); return false; }
      finally { versionActionBusy = false; syncVersionBoxDom(); }
    }'''
new_loader = '''    async function loadGithubVersion(version) {
      if (versionActionBusy || !canReloadAppVersion()) return false;
      const target = normalizeAppVersion(version);
      if (target === APP_VERSION) { setVersionHistoryStatus(`v${APP_VERSION} is running.`, "success", true); return true; }
      const restoreNewView = activeAppScreen === "newpage";
      try {
        if (restoreNewView) window.parent.__wh40kRestoreAppScreen = "newpage";
        else if (window.parent.__wh40kRestoreAppScreen === "newpage") delete window.parent.__wh40kRestoreAppScreen;
      } catch (_) {}
      versionActionBusy = true;
      setVersionHistoryStatus(`Loading v${target}…`, "", true);
      try {
        const loaded = await getVersionHost().load(target);
        if (!loaded && restoreNewView) {
          try { if (window.parent.__wh40kRestoreAppScreen === "newpage") delete window.parent.__wh40kRestoreAppScreen; } catch (_) {}
        }
        return loaded;
      }
      catch (error) {
        if (restoreNewView) {
          try { if (window.parent.__wh40kRestoreAppScreen === "newpage") delete window.parent.__wh40kRestoreAppScreen; } catch (_) {}
        }
        setVersionHistoryStatus(error.message, "error", true);
        return false;
      }
      finally { versionActionBusy = false; syncVersionBoxDom(); }
    }'''
once(old_loader, new_loader, 'version loader route preservation')

# Consume the marker only after the replacement runtime has successfully
# initialized its storage/model. Set New View before handing the runtime to the
# stable host so the first visible frame is already on the requested page.
old_ready = '''    ArmyBuilderModules.bootstrap.initialize().then(() => {
      if (!appStorageInitialized) throw new Error("App storage could not be opened. The current app was kept.");
      window.parent.WH40kVersionHost.ready(window, APP_VERSION);
    }).catch(error => window.parent.WH40kVersionHost.failed(window, error.message));'''
new_ready = '''    ArmyBuilderModules.bootstrap.initialize().then(() => {
      if (!appStorageInitialized) throw new Error("App storage could not be opened. The current app was kept.");
      let restoreNewView = false;
      try { restoreNewView = window.parent.__wh40kRestoreAppScreen === "newpage"; } catch (_) {}
      if (restoreNewView) showNewPageScreen();
      window.parent.WH40kVersionHost.ready(window, APP_VERSION);
      if (restoreNewView) {
        try { if (window.parent.__wh40kRestoreAppScreen === "newpage") delete window.parent.__wh40kRestoreAppScreen; } catch (_) {}
      }
    }).catch(error => window.parent.WH40kVersionHost.failed(window, error.message));'''
once(old_ready, new_ready, 'successful startup route restore')

# Release note.
note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.99
    Scope: Preserve New View across GitHub release switches. When loadGithubVersion starts while the top-level app is on New View, it records a one-shot route marker on the stable parent version host. After the replacement runtime completes bootstrap initialization, it restores New View before the host exposes the new runtime, then clears the marker. Failed loads clear the marker and retain the existing runtime. Old View/Edit/Cards version behavior is unchanged. Update-to-latest inherits the same behavior because it already routes through loadGithubVersion.
    Risk areas: Version-switch routing only. New View rendering, unified Edit, lock/frozen snapshot, Version/Update/Download grid placement, Old View/Edit/Cards, roster persistence, CSV data, Waha routing, and Probable remain unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.98\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

# Retain only the five newest detailed V31 notes.
notes = list(re.finditer(r'\n?  <!--\n    CHANGE NOTE - WH40k_11th_V31\.\d+\n.*?\n  -->\n', text, re.S))
for match in reversed(notes[5:]):
    text = text[:match.start()] + text[match.end():]

# Acceptance checks.
required = [
    '<title>WH40k 11th V31.99</title>',
    'The current baseline is WH40k_11th_V31.99;',
    'const APP_VERSION = "31.99";',
    "version: 'V31.99',",
    'const restoreNewView = activeAppScreen === "newpage";',
    'window.parent.__wh40kRestoreAppScreen = "newpage";',
    'restoreNewView = window.parent.__wh40kRestoreAppScreen === "newpage";',
    'if (restoreNewView) showNewPageScreen();',
    'window.parent.WH40kVersionHost.ready(window, APP_VERSION);',
    'return loadGithubVersion(entries[0].version);',
    'CHANGE NOTE - WH40k_11th_V31.99',
]
for value in required:
    if value not in text:
        raise SystemExit('V31.99 acceptance failed: ' + value)

# Ensure the current New View direct version buttons still use the parent loader.
if "parent.UI.loadGithubVersion(version)" not in text:
    raise SystemExit('V31.99 New View version button loader missing')

path.write_text(text, encoding='utf-8')
print('Built V31.99: New View route preserved across version loads')
