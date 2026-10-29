#!/usr/bin/env python3
"""Validate Unit_Profiles embedded weapons, loadouts, costs, and cross references."""
import csv
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ARMIES=('marines','orks','nids')
HEAD=['Unit_ID','Unit Name','M"','T','SV','W','LD','OC','Keywords','Hyperlink','Abilities','Other_Abilities']+[f'Point_{i}' for i in range(1,9)]+['Weapons']+[f'Loadout_{i}' for i in range(1,7)]

def read(path):
    with path.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        rows=list(reader)
        return reader.fieldnames,rows

def fail(message):
    raise SystemExit(message)

def split(line):
    return [x.strip() for x in re.split(r'\s+\|\s+',line)]

def attrs(parts,where):
    result={}
    for part in parts:
        if '=' not in part:fail(f'{where}: malformed {part!r}')
        key,value=part.split('=',1)
        key=key.lower()
        if key in result:fail(f'{where}: duplicate {key}')
        result[key]=value
    return result

def maxes(value,where):
    parts=(value or '').split(',')
    if len(parts)!=8 or any(not re.fullmatch(r'\d+',p.strip()) for p in parts):
        fail(f'{where}: expected 8 explicit nonnegative numeric limits')
    return [int(p) for p in parts]


def compact_to_legacy(value, slot, points, weapon_names, weapon_sets, where):
    """Expand compact loadout groups into the established strict validation grammar."""
    from urllib.parse import unquote
    match = re.fullmatch(r'(PER_MODEL|UNIT)(?::([\d/]+))?\s*(?:\[([^\]]*)\])?\s*\|\s*(.+)', value.strip(), re.S)
    if not match:fail(f'{where}/Loadout_{slot}: invalid compact group')
    mode, counts_text, group_text, options_text = match.groups()
    def metadata(source, location):
        out = {}
        for field in filter(None, (item.strip() for item in (source or '').split(';'))):
            if re.fullmatch(r'\+\d+', field):
                if 'cost' in out:fail(f'{location}: duplicate cost')
                out['cost'] = field[1:]
                continue
            if '=' not in field:fail(f'{location}: malformed compact metadata {field!r}')
            key, val = field.split('=', 1)
            key = key.lower().strip()
            if key in out:fail(f'{location}: duplicate compact attribute {key}')
            out[key] = unquote(val.strip())
        return out
    active = sum(points)
    def limits(source, location):
        tokens = source.split('/')
        if len(tokens)!=active or any(not re.fullmatch(r'\d+', x) for x in tokens):
            fail(f'{location}: expected {active} nonnegative limits')
        numbers = [0]*8
        it = iter(map(int, tokens))
        for i,present in enumerate(points):
            if present:numbers[i] = next(it)
        return numbers
    group = metadata(group_text, where)
    if not group.get('id'):fail(f'{where}/Loadout_{slot}: missing group id')
    if set(group)-{'id','label','section','count','allow','seq'}:
        fail(f'{where}/Loadout_{slot}: unknown group attribute {set(group)-{"id","label","section","count","allow","seq"}}')
    instances = limits(counts_text, where) if counts_text else [int(p) for p in points]
    if any(points[i] and instances[i]<1 for i in range(8)):
        fail(f'{where}/Loadout_{slot}: missing instances')
    group_id = group['id']
    name = group.get('label') or f'Weapon {slot}'
    heading = f'GROUP | {group_id} | {name} | mode={mode} | instances={",".join(map(str, instances))}'
    if group.get('section'):heading += f' | section={group["section"]}'
    if group.get('count'):heading += f' | count={group["count"]}'
    values = [heading]
    raw_options = [item.strip() for item in options_text.split(',') if item.strip()]
    if not raw_options:fail(f'{where}/Loadout_{slot}: no choices')
    marked = [v for v in raw_options if v.startswith('*')]
    if len(marked)>1:fail(f'{where}/Loadout_{slot}: multiple defaults')
    for n,item in enumerate(raw_options):
        mo = re.fullmatch(r'(\*)?([A-Za-z0-9_]+)(?:\s+\[([^\]]*)\])?', item)
        if not mo:fail(f'{where}/Loadout_{slot}: invalid option {item!r}')
        explicit, option_id, details = mo.groups()
        opt = metadata(details, where)
        if set(opt)-{'w','name','max','ability','allow','cost'}:
            fail(f'{where}/{group_id}/{option_id}: unknown option attribute')
        if 'w' in opt:
            weapon_ids = [] if opt['w']=='-' else opt['w'].split('+')
        elif option_id.upper() in weapon_sets:
            weapon_ids = weapon_sets[option_id.upper()]
        elif option_id in weapon_names:
            weapon_ids = [option_id]
        else:
            weapon_ids = []
            if option_id.upper()!='NONE' and not opt.get('ability'):
                fail(f'{where}/{group_id}/{option_id}: unknown Weapon_ID without mapping')
        for weapon_id in weapon_ids:
            if weapon_id not in weapon_names:
                fail(f'{where}/{group_id}/{option_id}: unknown Weapon_ID {weapon_id}')
        default_name = weapon_names.get(weapon_ids[0],option_id) if weapon_ids else ('None' if option_id=='NONE' else option_id.replace('_',' '))
        visible = opt.get('name') or default_name
        maximum = limits(opt['max'],where) if 'max' in opt else instances
        if any(maximum[i]>instances[i] for i in range(8)):
            fail(f'{where}/{group_id}/{option_id}: maximum exceeds instances')
        default = '1' if (bool(explicit) or (not marked and n==0)) else '0'
        value = f'OPTION | {option_id} | {visible} | default={default} | max={",".join(map(str,maximum))}'
        if weapon_ids:value += f' | weapons={",".join(weapon_ids)}'
        if opt.get('ability'):value += f' | abilities={opt["ability"].replace("+",",")}'
        compatibility = opt.get('allow',group.get('allow',''))
        if compatibility=='-':compatibility=''
        if compatibility:value += f' | compatible={compatibility.replace("/","|")}'
        if 'cost' in opt:value += f' | cost={opt["cost"]}'
        values.append(value)
    return values

def validate_army(army):
    directory=ROOT/'data'/army
    header,profiles=read(directory/'Unit_Profiles.csv')
    if header!=HEAD:fail(f'{army}: Unit_Profiles header mismatch')
    stats_rows=read(directory/'Weapon_Stats.csv')[1]
    weapon_names={r['Weapon_ID'].strip():r['Weapon Name'].strip() for r in stats_rows}
    weapons=set(weapon_names)
    weapon_sets={}
    for r in stats_rows:
        key=(r.get('Weapon_Set') or '').strip().upper()
        if key:
            raw_order=(r.get('Weapon_Set_Order') or '').strip()
            if not re.fullmatch(r'\d+',raw_order):fail(f'{army}: invalid Weapon_Set_Order for {r["Weapon_ID"]}')
            weapon_sets.setdefault(key,[]).append((int(raw_order),r['Weapon_ID'].strip()))
    for key,vals in weapon_sets.items():
        if len({n for n,_ in vals})!=len(vals):fail(f'{army}: repeated Weapon_Set_Order for {key}')
        weapon_sets[key]=[wid for _,wid in sorted(vals)]

    abilities={r['Ability_ID'].strip() for r in read(directory/'Abilities.csv')[1]}
    abilities|={r['Ability_ID'].strip() for r in read(ROOT/'data'/'universal'/'Universal_Abilities.csv')[1]}
    seen_units=set(); weapon_count=0; option_count=0; granted_count=0
    for profile in profiles:
        unit=(profile.get('Unit_ID') or '').strip()
        where=f'{army}/Unit_Profiles/{unit}'
        if not unit or unit in seen_units:fail(f'{where}: duplicate or missing Unit_ID')
        seen_units.add(unit)
        points=[bool((profile.get(f'Point_{i}') or '').strip()) for i in range(1,9)]
        if not points[0]:fail(f'{where}: missing Point_1')
        for field in ('Abilities','Other_Abilities'):
            ids=[x.strip() for x in (profile.get(field) or '').split(',') if x.strip()]
            if len(ids)!=len(set(ids)) or any(x not in abilities for x in ids):fail(f'{where}: invalid {field} Ability_ID')
        membership=set();fixed=set()
        for row in (x.strip() for x in (profile.get('Weapons') or '').splitlines() if x.strip()):
            p=split(row);kind=p.pop(0).upper()
            if kind not in ('WEAPON','FIXED','LABEL','BLANK'):fail(f'{where}: invalid weapon row type {kind}')
            value=p.pop(0) if kind!='BLANK' and p else ''
            metadata=attrs(p,where)
            if kind in ('WEAPON','FIXED'):
                if value not in weapons:fail(f'{where}: unknown Weapon_ID {value}')
                membership.add(value)
                if kind=='FIXED':fixed.add(value)
            elif kind=='LABEL' and not value:fail(f'{where}: empty LABEL')
            if metadata.get('qty') and not re.fullmatch(r'\d+',metadata['qty']):fail(f'{where}: invalid qty')
            if metadata.get('order') and not re.fullmatch(r'-?\d+',metadata['order']):fail(f'{where}: invalid order')
            weapon_count+=1
        groups={};selected=set()
        for slot in range(1,7):
            raw=(profile.get(f'Loadout_{slot}') or '').strip()
            cell=[x.strip() for x in raw.splitlines() if x.strip()]
            if not cell:continue
            if not re.match(r'^GROUP\s+\|',cell[0],re.I):
                cell=compact_to_legacy(raw,slot,points,weapon_names,weapon_sets,where)
            header=split(cell.pop(0))
            if len(header)<3 or header[0]!='GROUP' or not header[1] or not header[2]:fail(f'{where}/Loadout_{slot}: invalid GROUP')
            group_id=header[1]
            if group_id in groups:fail(f'{where}: duplicate group {group_id}')
            meta=attrs(header[3:],where)
            if meta.get('mode','UNIT') not in ('UNIT','PER_MODEL'):fail(f'{where}/{group_id}: invalid mode')
            instances=maxes(meta.get('instances'),where)
            if any(points[i] and instances[i]<1 or not points[i] and instances[i]!=0 for i in range(8)):fail(f'{where}/{group_id}: invalid instances')
            ids=set();compat=[];defaults=0
            for item in cell:
                p=split(item)
                if len(p)<3 or p[0]!='OPTION' or not p[1] or not p[2]:fail(f'{where}/{group_id}: invalid OPTION')
                opt_id=p[1]
                if opt_id in ids:fail(f'{where}/{group_id}: duplicate {opt_id}')
                ids.add(opt_id);option_count+=1
                values=attrs(p[3:],where)
                if values.get('default') not in ('0','1'):fail(f'{where}/{group_id}: missing default')
                defaults+=int(values['default'])
                limits=maxes(values.get('max'),where)
                if any(limits[i]>instances[i] for i in range(8)):fail(f'{where}/{group_id}/{opt_id}: max exceeds instances')
                if values['default']=='1' and any(points[i] and limits[i]<1 for i in range(8)):fail(f'{where}/{group_id}/{opt_id}: default limit zero')
                if values.get('cost') and not re.fullmatch(r'\d+(?:\.\d+)?',values['cost']):fail(f'{where}/{group_id}/{opt_id}: invalid cost')
                for name in (x.strip() for x in values.get('weapons','').split(',') if x.strip()):
                    if name not in weapons:fail(f'{where}/{group_id}/{opt_id}: unknown Weapon_ID {name}')
                    selected.add(name)
                for name in (x.strip() for x in values.get('preserve','').split(',') if x.strip()):
                    if name not in weapons:fail(f'{where}/{group_id}/{opt_id}: unknown preserved Weapon_ID {name}')
                for name in (x.strip() for x in values.get('abilities','').split(',') if x.strip()):
                    if name not in abilities:fail(f'{where}/{group_id}/{opt_id}: unknown Ability_ID {name}')
                    granted_count+=1
                for rule in (x for x in values.get('compatible','').split(';') if x):
                    if '=' not in rule:fail(f'{where}/{group_id}/{opt_id}: invalid compatibility {rule}')
                    target,allowed=rule.split('=',1)
                    compat.extend((target,a) for a in allowed.split('|') if a)
            if defaults!=1:fail(f'{where}/{group_id}: expected one default, found {defaults}')
            groups[group_id]=(ids,compat)
        if selected & fixed:fail(f'{where}: duplicate fixed/selectable weapons {sorted(selected&fixed)}')
        for group_id,(ids,compat) in groups.items():
            for target,allowed in compat:
                if target not in groups or allowed not in groups[target][0]:fail(f'{where}/{group_id}: unknown compatible option {target}={allowed}')
    print(f'{army}: loadouts OK: {len(profiles)} profiles, {weapon_count} weapon rows, {option_count} options, {granted_count} granted abilities')
    return True

if __name__=='__main__':
    for army in ARMIES:validate_army(army)
