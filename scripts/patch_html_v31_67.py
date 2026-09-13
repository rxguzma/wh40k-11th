from pathlib import Path
import html
import re

src = Path('versions/WH40k_11th_V31.66.html')
out = Path('WH40k_11th.html')
text = src.read_text(encoding='utf-8')

replacements = [
    ('<title>WH40k 11th V31.66</title>', '<title>WH40k 11th V31.67</title>'),
    ('The current baseline is WH40k_11th_V31.66;', 'The current baseline is WH40k_11th_V31.67;'),
    ('const APP_VERSION = "31.66";', 'const APP_VERSION = "31.67";'),
    ("version: 'V31.66',", "version: 'V31.67',"),
]
for old, new in replacements:
    if old not in text:
        raise SystemExit('version marker missing: ' + old)
    text = text.replace(old, new, 1)

frame_pattern = re.compile(r'(<iframe id="npViewFrame" class="np-view-frame" title="Alternate View" srcdoc=")(.*?)("></iframe>)', re.S)
match = frame_pattern.search(text)
if not match:
    raise SystemExit('alternate View iframe not found')
np = html.unescape(match.group(2))

# Remove the old static Nazdreg-era Deep Strike badge. Core-ability badges are
# now created from the active Unit's actual normalized Unit_Abilities mapping.
old_static_core = "  const ds=document.createElement('div');ds.className='detail-deep-strike unit-keyword';ds.textContent='DEEP STRIKE';f.appendChild(ds);\n"
if np.count(old_static_core) != 1:
    raise SystemExit(f'static Deep Strike badge: expected 1 match, found {np.count(old_static_core)}')
np = np.replace(old_static_core, '', 1)

old_exclusion = "if(el.matches('.detail-waha,.detail-deep-strike,.weapon-header,.weapon-row,.weapon-tags'))return;"
new_exclusion = "if(el.matches('.detail-waha,.detail-core-ability,.weapon-header,.weapon-row,.weapon-tags'))return;"
if np.count(old_exclusion) != 1:
    raise SystemExit(f'expanded-layout detail selector: expected 1 match, found {np.count(old_exclusion)}')
np = np.replace(old_exclusion, new_exclusion, 1)

old_mute = "grid.querySelectorAll('.detail-waha,.detail-deep-strike').forEach(el=>{el.classList.remove('keyword-muted');el.classList.toggle('detail-row-muted',hasSelection)});"
new_mute = "grid.querySelectorAll('.detail-waha,.detail-core-ability').forEach(el=>{el.classList.remove('keyword-muted');el.classList.toggle('detail-row-muted',hasSelection)});"
if np.count(old_mute) != 1:
    raise SystemExit(f'detail-row mute selector: expected 1 match, found {np.count(old_mute)}')
np = np.replace(old_mute, new_mute, 1)

old_waha_block = '''  const waha=grid.querySelector('.detail-waha');
  if(waha){
    const url=String(data&&data.waha||'').trim();
    waha.dataset.liveAvailable=url?'true':'false';
    waha.href=url||'#';
  }
  const weapons=data&&Array.isArray(data.weapons)?data.weapons:[];'''
new_waha_block = '''  const waha=grid.querySelector('.detail-waha');
  if(waha){
    const url=String(data&&data.waha||'').trim();
    waha.dataset.liveAvailable=url?'true':'false';
    waha.href=url||'#';
  }
  grid.querySelectorAll('.detail-core-ability').forEach(el=>el.remove());
  if(data){
    const coreAbilities=Array.isArray(data.coreAbilities)?data.coreAbilities:[];
    coreAbilities.slice(0,4).forEach((ability,index)=>{
      const label=String(ability&&ability.name||'').trim();
      if(!label)return;
      const tag=document.createElement('div');
      tag.className='detail-deep-strike unit-keyword detail-core-ability';
      tag.textContent=label.toUpperCase();
      tag.style.gridColumn=String(4+(index*3))+'/span 3';
      grid.appendChild(tag);
    });
  }
  const weapons=data&&Array.isArray(data.weapons)?data.weapons:[];'''
if np.count(old_waha_block) != 1:
    raise SystemExit(f'active Unit detail data block: expected 1 match, found {np.count(old_waha_block)}')
np = np.replace(old_waha_block, new_waha_block, 1)

old_visibility = '''  const deep=grid.querySelector('.detail-deep-strike');
  if(deep){deep.style.gridRow=String(detailStartRow);deep.style.display=activeUnitIndex!==null?'flex':'none'}
  syncWeaponLayout();'''
new_visibility = '''  grid.querySelectorAll('.detail-core-ability').forEach(el=>{
    el.style.gridRow=String(detailStartRow);
    el.style.display=activeUnitIndex!==null?'flex':'none';
  });
  syncWeaponLayout();'''
if np.count(old_visibility) != 1:
    raise SystemExit(f'core-ability visibility block: expected 1 match, found {np.count(old_visibility)}')
np = np.replace(old_visibility, new_visibility, 1)

np_checks = [
    "grid.querySelectorAll('.detail-core-ability').forEach(el=>el.remove());",
    "const coreAbilities=Array.isArray(data.coreAbilities)?data.coreAbilities:[];",
    "tag.className='detail-deep-strike unit-keyword detail-core-ability';",
    "tag.style.gridColumn=String(4+(index*3))+'/span 3';",
    "grid.querySelectorAll('.detail-waha,.detail-core-ability')",
]
missing_np = [value for value in np_checks if value not in np]
if missing_np:
    raise SystemExit('alternate View core-ability check failed: ' + ', '.join(missing_np))
if "ds.textContent='DEEP STRIKE'" in np:
    raise SystemExit('static Deep Strike text still present')

np_srcdoc = html.escape(np, quote=True)
text = text[:match.start(2)] + np_srcdoc + text[match.end(2):]

# Return each Unit's actual canonical CORE_ABILITY records alongside Waha and
# Weapons. This uses the existing normalized runtime helper rather than names or
# Unit-specific exceptions.
old_bridge = '''        waha: getUnitWahapediaLink(unit),
        weapons: weapons.slice(0,5).map(weapon => {'''
new_bridge = '''        waha: getUnitWahapediaLink(unit),
        coreAbilities: unit ? getCoreAbilitiesForUnit(unit)
          .filter(ability => ability && !ability.isMissingLink)
          .map(ability => ({ name: String(ability.name || ability.abilityId || "") })) : [],
        weapons: weapons.slice(0,5).map(weapon => {'''
if text.count(old_bridge) != 1:
    raise SystemExit(f'Unit data bridge core abilities: expected 1 match, found {text.count(old_bridge)}')
text = text.replace(old_bridge, new_bridge, 1)

note = '''  <!--
    CHANGE NOTE - WH40k_11th_V31.67
    Scope: Make the alternate-View row under each wired Unit data-driven. Waha remains first, followed only by that active Unit's canonical CORE_ABILITY entries from Unit_Abilities.csv resolved through the existing runtime ability data. Remove the hardcoded Deep Strike badge. For the current first two Edit-order Units, Nazdreg therefore shows Waha + Deep Strike while Meganobz shows Waha only. Core-ability badges retain the existing Deep Strike badge visual standard and the existing Weapon-selection muted-text behavior.
    Risk areas: Alternate View first/second Unit detail row only. Unit ordering, profile stats, Waha URLs, Weapon filtering/selection, canonical View/Edit/Cards, persistence, and combat behavior are unchanged.
  -->

'''
mark = '  <!--\n    CHANGE NOTE - WH40k_11th_V31.66\n'
if mark in text:
    text = text.replace(mark, note + mark, 1)
elif '</body>' in text:
    text = text.replace('</body>', note + '</body>', 1)
else:
    raise SystemExit('release note insertion point missing')

text = re.sub(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.62\n.*?\n  -->\n', '\n', text, count=1, flags=re.S)

checks = [
    '<title>WH40k 11th V31.67</title>',
    'const APP_VERSION = "31.67";',
    "version: 'V31.67',",
    'coreAbilities: unit ? getCoreAbilitiesForUnit(unit)',
    'detail-core-ability',
    'CHANGE NOTE - WH40k_11th_V31.67',
]
missing = [value for value in checks if value not in text]
if missing:
    raise SystemExit('acceptance check failed: ' + ', '.join(missing))

out.write_text(text, encoding='utf-8')
print('Built V31.67: Waha plus data-driven CORE_ABILITY row for wired Units')
