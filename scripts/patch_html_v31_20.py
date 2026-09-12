from pathlib import Path
import re

source = Path("versions/WH40k_11th_V31.19.html")
path = Path("WH40k_11th.html")
text = source.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    text = text.replace(old, new, 1)


# Sequential release metadata.
replace_once('<title>WH40k 11th V31.19</title>', '<title>WH40k 11th V31.20</title>', 'title version')
replace_once('The current baseline is WH40k_11th_V31.19;', 'The current baseline is WH40k_11th_V31.20;', 'maintenance baseline')
replace_once('const APP_VERSION = "31.19";', 'const APP_VERSION = "31.20";', 'APP_VERSION')
replace_once("version: 'V31.19',", "version: 'V31.20',", 'InternalQuality version')

# Do not render or calculate Probable while a Unit detail panel is being built.
old_probable_mount = '''<div class="subsection active-unit-detail-box" id="probable-${index}">${renderProbablePanel(entry, unit)}</div>'''
new_probable_mount = '''<div class="subsection active-unit-detail-box" id="probable-${index}" data-probable-entry-id="${escapeAttr(entry.entryId || "")}"></div>'''
replace_once(old_probable_mount, new_probable_mount, 'lazy Probable mount')

# The first click that opens Probable now performs the initial render/calculation.
old_toggle = '''    function toggleSection(index, selectedSection) { const section = document.getElementById(`${selectedSection}-${index}`); const button = document.getElementById(`btn-${selectedSection}-${index}`); const isOpen = section.style.display === "block"; section.style.display = isOpen ? "none" : "block"; button.classList.toggle("active", !isOpen); }'''
new_toggle = '''    function ensureProbableSectionRendered(index) {
      const section = document.getElementById(`probable-${index}`);
      if (!section) return false;
      if (section.dataset.probableLoaded === "true") return true;
      const entryId = String(section.dataset.probableEntryId || "").trim();
      if (!entryId) return false;
      const roster = getActiveRoster();
      const entry = getRosterEntryById(roster, entryId);
      const unit = entry ? getUnitById(entry.unitId) : null;
      if (!entry || !unit) return false;
      section.innerHTML = renderProbablePanel(entry, unit);
      section.dataset.probableLoaded = "true";
      return true;
    }

    function toggleSection(index, selectedSection) {
      const section = document.getElementById(`${selectedSection}-${index}`);
      const button = document.getElementById(`btn-${selectedSection}-${index}`);
      if (!section || !button) return;
      const isOpen = section.style.display === "block";
      if (!isOpen && selectedSection === "probable") ensureProbableSectionRendered(index);
      section.style.display = isOpen ? "none" : "block";
      button.classList.toggle("active", !isOpen);
    }'''
replace_once(old_toggle, new_toggle, 'lazy Probable toggle')

# Until Probable has been opened, refresh requests from weapon/ability/tag UI must
# exit before looking up the roster entry or invoking any Probable rendering.
old_refresh = '''    function refreshProbableSection(entryId) {
      const cleanEntryId = String(entryId || "").trim();
      if (!cleanEntryId || appEditMode) return false;
      const roster = getActiveRoster();
      const entry = getRosterEntryById(roster, cleanEntryId);
      const unit = entry ? getUnitById(entry.unitId) : null;
      if (!entry || !unit) return false;
      const body = Array.from(document.querySelectorAll("[data-probable-section-for]"))
        .find(node => String(node.dataset.probableSectionFor || "") === cleanEntryId);
      if (!body) return false;
      const wrapper = document.createElement("div");
      wrapper.innerHTML = renderProbablePanel(entry, unit);
      const replacement = wrapper.querySelector("[data-probable-section-for]");
      if (!replacement) return false;
      body.replaceWith(replacement);
      return true;
    }'''
new_refresh = '''    function refreshProbableSection(entryId) {
      const cleanEntryId = String(entryId || "").trim();
      if (!cleanEntryId || appEditMode) return false;
      const body = Array.from(document.querySelectorAll("[data-probable-section-for]"))
        .find(node => String(node.dataset.probableSectionFor || "") === cleanEntryId);
      if (!body) return false;
      const roster = getActiveRoster();
      const entry = getRosterEntryById(roster, cleanEntryId);
      const unit = entry ? getUnitById(entry.unitId) : null;
      if (!entry || !unit) return false;
      const wrapper = document.createElement("div");
      wrapper.innerHTML = renderProbablePanel(entry, unit);
      const replacement = wrapper.querySelector("[data-probable-section-for]");
      if (!replacement) return false;
      body.replaceWith(replacement);
      return true;
    }'''
replace_once(old_refresh, new_refresh, 'Probable refresh gate')

# Add the new detailed release note and keep only the five newest detailed notes.
note_marker = "  <!--\n    CHANGE NOTE - WH40k_11th_V31.19\n"
if note_marker not in text:
    raise SystemExit("release note insertion marker missing")
new_note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.20
    Scope: Make Probable truly lazy in View mode. Opening a Unit no longer renders or calculates the Probable panel; the first Probable button click initializes it. Weapon, Ability, and Tag refresh hooks do nothing until Probable has been opened at least once for that rendered Unit detail.
    Risk areas: View-mode Probable initialization and refresh timing only. Existing Probable calculations, controls, selected-weapon behavior, and non-Probable Unit sections are unchanged.
  -->

'''
text = text.replace(note_marker, new_note + note_marker, 1)
old_note_pattern = re.compile(r"\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.15\n.*?\n  -->\n", re.S)
text, removed = old_note_pattern.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit(f"old release note removal: expected 1 match, found {removed}")

checks = [
    '<title>WH40k 11th V31.20</title>',
    'const APP_VERSION = "31.20";',
    "version: 'V31.20',",
    'CHANGE NOTE - WH40k_11th_V31.20',
    'data-probable-entry-id="${escapeAttr(entry.entryId || "")}"></div>',
    'function ensureProbableSectionRendered(index)',
    'if (!isOpen && selectedSection === "probable") ensureProbableSectionRendered(index);',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))
if old_probable_mount in text:
    raise SystemExit('eager Probable mount still present')
if 'const body = Array.from(document.querySelectorAll("[data-probable-section-for]"))' not in text:
    raise SystemExit('Probable refresh rendered-body gate missing')

path.write_text(text, encoding="utf-8")
print("Built WH40k_11th.html as V31.20 with click-only Probable initialization")
