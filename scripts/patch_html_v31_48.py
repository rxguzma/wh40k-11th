from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.47.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')


def r(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    text = text.replace(old, new, 1)


r('<title>WH40k 11th V31.47</title>', '<title>WH40k 11th V31.48</title>', 'title')
r('The current baseline is WH40k_11th_V31.47;', 'The current baseline is WH40k_11th_V31.48;', 'baseline')
r('const APP_VERSION = "31.47";', 'const APP_VERSION = "31.48";', 'APP_VERSION')
r("version: 'V31.47',", "version: 'V31.48',", 'quality version')

# Pull out the transferred alternate-View document so its literal grid rows can
# be changed without reconstructing any visual standards.
frame_pattern = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
match = frame_pattern.search(text)
if not match:
    raise SystemExit('alternate View iframe not found')
np = html.unescape(match.group(2))

# Requested literal row moves only.
old_deep = '.detail-deep-strike{grid-column:1/span 3;grid-row:24;z-index:3;align-self:center;'
new_deep = '.detail-deep-strike{grid-column:1/span 3;grid-row:10;z-index:3;align-self:center;'
if np.count(old_deep) != 1:
    raise SystemExit(f'Deep Strike row: expected 1 match, found {np.count(old_deep)}')
np = np.replace(old_deep, new_deep, 1)

old_rows = '.weapon-row-1{grid-row:28}.weapon-tags-1{grid-row:29}.weapon-row-2{grid-row:31}.weapon-tags-2{grid-row:32}.weapon-row-3{grid-row:34}.weapon-tags-3{grid-row:35}.weapon-row-4{grid-row:37}.weapon-tags-4{grid-row:38}.weapon-row-5{grid-row:40}.weapon-tags-5{grid-row:41}'
new_rows = '.weapon-row-1{grid-row:11}.weapon-tags-1{grid-row:12}.weapon-row-2{grid-row:31}.weapon-tags-2{grid-row:32}.weapon-row-3{grid-row:34}.weapon-tags-3{grid-row:35}.weapon-row-4{grid-row:37}.weapon-tags-4{grid-row:38}.weapon-row-5{grid-row:40}.weapon-tags-5{grid-row:41}'
if np.count(old_rows) != 1:
    raise SystemExit(f'first weapon rows: expected 1 match, found {np.count(old_rows)}')
np = np.replace(old_rows, new_rows, 1)

# Extend the existing Nazdreg live refresh to the one moved first weapon row and
# its existing Tag row. Do not wire any other weapon/mock content yet.
old_refresh_tail = '''  [data.m,data.t,data.sv,data.w,data.ld,data.oc].forEach((value,index)=>{const cell=row.querySelector('.s'+(index+1));if(cell)cell.textContent=String(value??'')});
  return true;
}'''
new_refresh_tail = '''  [data.m,data.t,data.sv,data.w,data.ld,data.oc].forEach((value,index)=>{const cell=row.querySelector('.s'+(index+1));if(cell)cell.textContent=String(value??'')});
  const weaponRow=grid.querySelector('.weapon-row-1');
  if(weaponRow){
    const weapon=data.weapon||null;
    weaponRow.style.display=weapon?'grid':'none';
    if(weapon){
      const weaponName=weaponRow.querySelector('.weapon-name');
      if(weaponName)weaponName.textContent=String(weapon.name||'');
      [weapon.range,weapon.attacks,weapon.skill,weapon.strength,weapon.ap,weapon.damage].forEach((value,index)=>{const cell=weaponRow.querySelector('.wr'+(index+1));if(cell)cell.textContent=String(value??'')});
    }
  }
  const tagRow=grid.querySelector('.weapon-tags-1');
  if(tagRow){
    const tags=data.weapon&&Array.isArray(data.weapon.tags)?data.weapon.tags:[];
    const tagEls=[...tagRow.querySelectorAll('.weapon-tag')];
    tagEls.forEach((el,index)=>{el.textContent=String(tags[index]||'');el.style.display=tags[index]?'inline-flex':'none'});
    tagRow.style.display=tags.length?'grid':'none';
  }
  return true;
}'''
if np.count(old_refresh_tail) != 1:
    raise SystemExit(f'Nazdreg refresh tail: expected 1 match, found {np.count(old_refresh_tail)}')
np = np.replace(old_refresh_tail, new_refresh_tail, 1)

np_srcdoc = html.escape(np, quote=True)
text = text[:match.start(2)] + np_srcdoc + text[match.end(2):]

# Extend the already-scoped parent bridge with only Nazdreg's first real weapon
# from the current Edit/active roster data.
old_return = '''      const stats = model.stats || {};
      return {
        name: String(model.displayName || (model.unit && model.unit.name) || "Nazdreg"),
        m: String(stats.m ?? ""),
        t: String(stats.t ?? ""),
        sv: String(stats.sv ?? ""),
        w: String(stats.w ?? ""),
        ld: String(stats.ld ?? ""),
        oc: String(stats.oc ?? "")
      };'''
new_return = '''      const stats = model.stats || {};
      const entry = model.entry || (roster && Array.isArray(roster.entries) ? roster.entries.find(item => item && item.entryId === model.entryId) : null);
      const unit = model.unit || (entry ? getUnitById(entry.unitId) : null);
      const weapons = entry && unit ? getWeaponsForRosterEntry(entry, unit).filter(item => item && !item.isMissingLink) : [];
      const weapon = weapons[0] || null;
      const tags = weapon ? splitWeaponAbilities(weapon.weaponAbility) : [];
      return {
        name: String(model.displayName || (model.unit && model.unit.name) || "Nazdreg"),
        m: String(stats.m ?? ""),
        t: String(stats.t ?? ""),
        sv: String(stats.sv ?? ""),
        w: String(stats.w ?? ""),
        ld: String(stats.ld ?? ""),
        oc: String(stats.oc ?? ""),
        weapon: weapon ? {
          name: String(weapon.name || weapon.weaponId || ""),
          range: String(weapon.range ?? ""),
          attacks: String(weapon.attacks ?? ""),
          skill: String(weapon.skill ?? ""),
          strength: String(weapon.strength ?? ""),
          ap: String(weapon.ap ?? ""),
          damage: String(weapon.damage ?? ""),
          tags
        } : null
      };'''
r(old_return, new_return, 'Nazdreg live weapon bridge')

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.48
    Scope: In the alternate View, move the existing Deep Strike row from grid row 24 to row 10, move the first Nazdreg Weapon row from row 28 to row 11, and move its existing Tag row from row 29 to row 12. Wire only that first Weapon row and its existing Tag badges to Nazdreg's real current Edit/active-roster Weapon data (name, R, A, WS, St, AP, D, and Weapon Ability labels). Leave every other transferred Weapon and mock row unchanged.
    Risk areas: Alternate View Nazdreg rows 10-12 and the existing Nazdreg parent data bridge only. Canonical View/Edit/Cards, roster persistence, combat behavior, and all other alternate-View rows are unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.47\n'
if mark not in text:
    raise SystemExit('release note marker missing')
text = text.replace(mark, note + mark, 1)
text, removed = re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.43\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)
if removed != 1:
    raise SystemExit(f'old note removal: expected 1 match, found {removed}')

checks = [
    '<title>WH40k 11th V31.48</title>',
    'const APP_VERSION = "31.48";',
    "version: 'V31.48',",
    'grid-row:10;z-index:3;align-self:center;',
    '.weapon-row-1{grid-row:11}.weapon-tags-1{grid-row:12}',
    'weaponRow=grid.querySelector(&#x27;.weapon-row-1&#x27;)',
    'getWeaponsForRosterEntry(entry, unit)',
    'splitWeaponAbilities(weapon.weaponAbility)',
    'weapon: weapon ? {',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('static acceptance checks failed: ' + ', '.join(missing))

out.write_text(text, encoding='utf-8')
print('Built V31.48 with Nazdreg rows 10-12 and first live Weapon')
