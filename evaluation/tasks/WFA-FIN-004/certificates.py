"""Central affine certificates; exact cancellation precedes subset selection."""
from itertools import combinations, product
from algebra import parse, polynomial_quotient, substitute_polynomial
from ranking import one, two


def symbol_names(expr):
    import ast
    return {n.id for n in ast.walk(ast.parse(expr, mode='eval')) if isinstance(n, ast.Name)}


def identified_models(exprs, params, scenario, alpha_max=1):
    continuous = [p for p in params if p != 'p']
    known = {}
    for issuer, expr in exprs.items():
        syms = symbol_names(expr)
        a, b = parse(expr, syms)
        # Cancel only after parse has certified every original denominator.
        mapping = {'p': scenario} if scenario is not None else {}
        a, b = substitute_polynomial(a, mapping), substitute_polynomial(b, mapping)
        reduced = polynomial_quotient(a, b)
        if reduced is None:
            # A genuine financial denominator retains source uncertainty.
            continue
        a = reduced
        if any(sum(name in continuous for name in mon)>1 for mon in a):
            raise ValueError('policy model must be affine in common parameters')
        substituted = {}
        for mon, coef in a.items():
            if scenario is not None and 'p' in mon:
                coef *= scenario ** mon.count('p')
                mon = tuple(x for x in mon if x != 'p')
            substituted[mon] = substituted.get(mon, 0) + coef
        if any(coef and set(mon) - set(continuous) for mon, coef in substituted.items()):
            continue
        intercept = float(substituted.get((), 0))
        coeff = [intercept]
        for p in continuous:
            coeff.append(float(substituted.get((p,), 0)) * (alpha_max if p == 'alpha' else 1))
        known[issuer] = coeff if continuous else coeff + [0.]
    return known


def certificate(exprs, params, scenario=None, alpha_max=1):
    known = identified_models(exprs, params, scenario, alpha_max)
    if not known:
        return {'identified_subset': [], 'always_top_two': [], 'possible_top_two': [],
                'robust_pairs': [], 'leave_one_out': {}, 'endpoints': {}, 'crossings': {}}
    cert = two(known) if len(next(iter(known.values()))) == 3 else one(known)
    dims = len(next(iter(known.values()))) - 1
    endpoints = {}
    for theta in product([0, 1], repeat=dims):
        vals = {t: co[0] + sum(x*y for x, y in zip(co[1:], theta)) for t, co in known.items()}
        ranks = {t: 1 + sum(x > y + 1e-10 for x in vals.values()) for t, y in vals.items()}
        endpoints[','.join(map(str, theta))] = {'ranks': ranks,
                                               'top_two': sorted(t for t in vals if ranks[t] <= 2)}
    crossings = {}
    if dims == 1:
        for a, b in combinations(sorted(known), 2):
            slope = known[a][1] - known[b][1]
            if abs(slope) <= 1e-12:
                root = 'identical' if abs(known[a][0]-known[b][0]) <= 1e-12 else 'parallel'
            else:
                x = -(known[a][0]-known[b][0])/slope
                root = round(x, 10) if 0 < x < 1 else 'outside_open_domain'
            crossings[a+'/'+b] = root
    return {'identified_subset': sorted(known), 'always_top_two': cert['always_top_two'],
            'possible_top_two': cert['possible_top_two'],
            'robust_pairs': sorted('>'.join(p) for p in cert['robust_pairs']),
            'leave_one_out': {t: {'always_top_two': z['always_top_two'],
                                  'possible_top_two': z['possible_top_two'],
                                  'robust_pairs': sorted('>'.join(p) for p in z['robust_pairs'])}
                              for t, z in cert['leave_one_out'].items()},
            'endpoints': endpoints, 'crossings': crossings}
