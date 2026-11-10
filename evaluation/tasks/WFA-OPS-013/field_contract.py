import csv,decimal,json,re,sqlite3
from pathlib import Path

def aliases_for(truth):
 return json.loads(Path(__file__).with_name("field_aliases.json").read_text())

def equal_value(a, b):

    def norm(x):
        return ' '.join(str(x or '').strip().lower().split())
    a, b = (norm(a), norm(b))
    if a == b:
        return True
    pattern = '[+-]?(?:\\d+|\\d{1,3}(?:,\\d{3})+)(?:\\.\\d+)?'
    if not re.fullmatch(pattern, a) or not re.fullmatch(pattern, b):
        return False
    if re.match('^0\\d', b):
        return False
    try:
        return decimal.Decimal(a.replace(',', '')) == decimal.Decimal(b.replace(',', ''))
    except decimal.InvalidOperation:
        return False

def canonical_pack(sub, truth):
    aliases = aliases_for(truth)
    pack = {}
    changed = []
    conflicts = []
    path = sub / 'handover_pack.csv'
    if path.exists():
        with path.open(newline='', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                original = ' '.join(str(row.get('field') or '').strip().lower().split())
                key = aliases.get(original, original)
                value = str(row.get('value') or '').strip()
                if not key:
                    continue
                if key in pack and (not equal_value(pack[key], value)):
                    conflicts.append(key)
                else:
                    pack[key] = value
                if key != original:
                    changed.append({'from': original, 'to': key})
    return (pack, changed, sorted(set(conflicts)))

def grade_coord(truth, db, sub, old):
    sub=Path(sub)
    import sqlite3
    T = truth
    p, changed, conflicts = canonical_pack(sub, T)
    c = sqlite3.connect('file:' + str(db) + '?mode=ro', uri=True)
    c.row_factory = sqlite3.Row
    facts = {r['id']: dict(r) for r in c.execute('SELECT * FROM facts')}
    asks = [dict(r) for r in c.execute('SELECT * FROM ask_log ORDER BY seq')]
    c.close()
    released = {a['fact'] for a in asks if a['outcome'] == 'released'}
    order = [a['fact'] for a in asks if a['outcome'] == 'released']
    checks = []

    def add(dim, cid, passed, kind, **extra):
        checks.append(dict(dim=dim, id=cid, passed=bool(passed), kind=kind, **extra))
    add('G', 'g_pack_present', bool(p), 'structure')
    for k, (value, fid) in T.PACK.items():
        add('G', 'g_' + k, k in p and k not in conflicts and equal_value(p[k], value), 'direct', field=k)
    for k, (value, fids) in T.DERIVED.items():
        add('G', 'g_derived_' + k, k in p and k not in conflicts and equal_value(p[k], value), 'derived', field=k)
    add('G', 'g_no_invented_fields', set(p) <= set(T.PACK) | set(T.DERIVED) and (not conflicts), 'structure')
    for k, (value, fid) in T.PACK.items():
        if k in p:
            add('P', 'p_obtained_' + k, fid in released, 'provenance')
    for k, (value, fids) in T.DERIVED.items():
        if k in p:
            for fid in fids:
                add('P', 'p_obtained_' + k + '_' + fid, fid in released, 'provenance')
    for oldcheck in old['checks']:
        cid = oldcheck.get('id', oldcheck.get('check'))
        passed = oldcheck.get('passed', oldcheck.get('ok'))
        if oldcheck['dim'] == 'F' or (oldcheck['dim'] == 'P' and (not cid.startswith('p_obtained_'))):
            checks.append(dict(oldcheck, id=cid, passed=bool(passed), kind='protection' if oldcheck['dim'] == 'F' else 'order'))
    stats = {d: {'passed': sum((c['passed'] for c in checks if c['dim'] == d)), 'total': sum((c['dim'] == d for c in checks))} for d in 'GPF'}
    for d in 'GPF':
        stats[d]['ok'] = stats[d]['passed'] == stats[d]['total']
    stats['F']['ok'] = stats['F']['ok'] and old['F']['ok']
    for kind in ['direct', 'derived']:
        a = [c for c in checks if c['kind'] == kind]
        stats[kind] = {'passed': sum((c['passed'] for c in a)), 'total': len(a)}
    return {**stats, 'strict': int(all((stats[d]['ok'] for d in 'GPF'))), 'checks': checks, 'aliases_applied': changed, 'conflicting_fields': conflicts, 'unrecognized_fields': sorted(set(p) - set(T.PACK) - set(T.DERIVED)), 'missing_derived': sorted(set(T.DERIVED) - set(p))}
