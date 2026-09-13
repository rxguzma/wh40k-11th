from pathlib import Path
import re

src = Path('versions/WH40k_11th_V31.69.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


replace_once('<title>WH40k 11th V31.69</title>', '<title>WH40k 11th V31.70</title>', 'title')
replace_once('The current baseline is WH40k_11th_V31.69;', 'The current baseline is WH40k_11th_V31.70;', 'baseline')
replace_once('const APP_VERSION = "31.69";', 'const APP_VERSION = "31.70";', 'APP_VERSION')
replace_once("version: 'V31.69',", "version: 'V31.70',", 'quality version')

# Route Alternate View Waha through the top-level version host when present.
old_helper = '''    function openAlternateViewWaha(url) {
      const href = String(url || '').trim();
      if (!/^https?:\\/\\//i.test(href)) return false;
      try {
        window.open(href, '_blank', 'noopener');
        return true;
      } catch (_) {
        return false;
      }
    }
    window.openAlternateViewWaha = openAlternateViewWaha;
'''
new_helper = '''    function openAlternateViewWaha(url) {
      const href = String(url || '').trim();
      if (!/^https?:\\/\\//i.test(href)) return false;
      try {
        const host = window.parent && window.parent.WH40kVersionHost;
        if (host && typeof host.openExternal === 'function') return host.openExternal(href);
        window.open(href, '_blank', 'noopener');
        return true;
      } catch (_) {
        return false;
      }
    }
    window.openAlternateViewWaha = openAlternateViewWaha;
'''
replace_once(old_helper, new_helper, 'Alternate View host-routed Waha helper')

# The release host exists twice in the standalone source: once as the active host
# and once as the passive source used to reconstruct future standalone downloads.
host_vars_old = '''  let changing = false;
  let saving = false;
  let entries = [];'''
host_vars_new = '''  let changing = false;
  let saving = false;
  let entries = [];
  let externalNavigationPending = false;
  let externalRecoveryQueued = false;'''
if text.count(host_vars_old) != 2:
    raise SystemExit(f'host state block: expected 2 matches, found {text.count(host_vars_old)}')
text = text.replace(host_vars_old, host_vars_new, 2)

recovery_block = '''
  function recoverRuntimeAfterExternalNavigation() {
    if (!externalNavigationPending || externalRecoveryQueued || changing || !active) return;
    externalNavigationPending = false;
    externalRecoveryQueued = true;
    const expected = active;
    let responded = false;
    const timer = setTimeout(() => {
      if (responded || active !== expected) {
        externalRecoveryQueued = false;
        return;
      }
      const release = { version: expected.version, html: expected.html, runtime: expected.runtime };
      changing = true;
      mount(release).catch(error => {
        errorBox.textContent = "App recovery failed: " + error.message;
        errorBox.hidden = false;
      }).finally(() => {
        changing = false;
        externalRecoveryQueued = false;
        if (active && active.frame) active.frame.inert = false;
      });
    }, 500);
    try {
      const target = expected.frame && expected.frame.contentWindow;
      if (target && typeof target.requestAnimationFrame === "function") {
        target.requestAnimationFrame(() => {
          if (active !== expected) return;
          responded = true;
          clearTimeout(timer);
          externalRecoveryQueued = false;
        });
      }
    } catch (_) {}
  }

  function queueExternalNavigationRecovery() {
    if (!externalNavigationPending || externalRecoveryQueued) return;
    setTimeout(recoverRuntimeAfterExternalNavigation, 50);
  }

'''
host_object_marker = '  window.WH40kVersionHost = Object.freeze({\n'
if text.count(host_object_marker) != 2:
    raise SystemExit(f'host object marker: expected 2 matches, found {text.count(host_object_marker)}')
text = text.replace(host_object_marker, recovery_block + host_object_marker, 2)

open_external_method = '''    openExternal(url) {
      const href = String(url || "").trim();
      if (!/^https?:\\/\\//i.test(href)) throw new Error("External URL must use HTTP or HTTPS.");
      externalNavigationPending = true;
      const link = document.createElement("a");
      link.href = href;
      link.target = "_blank";
      link.rel = "noopener";
      document.body.appendChild(link);
      link.click();
      link.remove();
      return true;
    },
'''
object_start = '  window.WH40kVersionHost = Object.freeze({\n    async history() {'
object_replacement = '  window.WH40kVersionHost = Object.freeze({\n' + open_external_method + '    async history() {'
if text.count(object_start) != 2:
    raise SystemExit(f'host openExternal insertion: expected 2 matches, found {text.count(object_start)}')
text = text.replace(object_start, object_replacement, 2)

resume_listeners = '''
  window.addEventListener("pageshow", queueExternalNavigationRecovery);
  window.addEventListener("focus", queueExternalNavigationRecovery);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") queueExternalNavigationRecovery();
  });

'''
class_marker = '  document.documentElement.classList.add("wh40k-version-host");\n'
if text.count(class_marker) != 2:
    raise SystemExit(f'host resume listener insertion: expected 2 matches, found {text.count(class_marker)}')
text = text.replace(class_marker, resume_listeners + class_marker, 2)

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.70
    Scope: Recover the V31 version-host runtime after returning from an external Waha navigation. Alternate View Waha now asks the top-level version host to open the existing HTTPS URL. The host marks that navigation, and on pageshow/focus/visibility return it probes the active runtime iframe. If the runtime still responds, nothing changes; if the restored iframe is dead, the host remounts the already-loaded release without fetching a new version. No Waha URL/data or visible UI changes.
    Risk areas: V31 version-host external-navigation return path and Alternate View Waha routing only. Roster persistence, View/Edit/Cards behavior, CSV data, weapons, combat behavior, and version selection remain unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.69\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.65\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

checks = [
    '<title>WH40k 11th V31.70</title>',
    'const APP_VERSION = "31.70";',
    "version: 'V31.70',",
    "typeof host.openExternal === 'function'",
    'let externalNavigationPending = false;',
    'function recoverRuntimeAfterExternalNavigation()',
    'openExternal(url) {',
    'window.addEventListener("pageshow", queueExternalNavigationRecovery);',
    'CHANGE NOTE - WH40k_11th_V31.70',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('acceptance check failed: ' + ', '.join(missing))
if text.count('openExternal(url) {') != 2:
    raise SystemExit('expected active and passive host openExternal methods')
if text.count('window.addEventListener("pageshow", queueExternalNavigationRecovery);') != 2:
    raise SystemExit('expected active and passive host return listeners')

out.write_text(text, encoding='utf-8')
print('Built V31.70: version host probes/remounts a dead runtime after Waha return')
