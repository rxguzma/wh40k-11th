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

def validate_army(army):
    directory=ROOT/'data'/army
    header,profiles=read(directory/'Unit_Profiles.csv')
    if header!=HEAD:fail(f'{army}: Unit_Profiles header mismatch')
    weapons={r['Weapon_ID'].strip() for r in read(directory/'Weapon_Stats.csv')[1]}
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
            cell=[x.strip() for x in (profile.get(f'Loadout_{slot}') or '').splitlines() if x.strip()]
            if not cell:continue
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
