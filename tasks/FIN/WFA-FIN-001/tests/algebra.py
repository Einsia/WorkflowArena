"""Small exact rational-function checker. Parses arithmetic, never executes code."""
import ast
from fractions import Fraction

MAX_TERMS = 4096


def clean(p):
    p = {k: v for k, v in p.items() if v}
    if len(p) > MAX_TERMS:
        raise ValueError('expression too large')
    return p


def add(a, b, sign=1):
    out = dict(a)
    for k, v in b.items():
        out[k] = out.get(k, 0) + sign * v
    return clean(out)


def mul(a, b):
    if len(a) * len(b) > MAX_TERMS:
        raise ValueError('expression too large')
    out = {}
    for x, v in a.items():
        for y, w in b.items():
            key = tuple(sorted(x + y))
            if len(key) > 12:
                raise ValueError('degree too high')
            out[key] = out.get(key, 0) + v * w
    return clean(out)


ONE = {(): Fraction(1)}


def parse(text, allowed):
    if not isinstance(text, str) or len(text) > 12000:
        raise ValueError('expression must be a short string')
    tree = ast.parse(text, mode='eval')
    if sum(1 for _ in ast.walk(tree)) > 1500:
        raise ValueError('expression too large')

    def walk(n):
        if isinstance(n, ast.Constant) and type(n.value) in (int, float):
            # Use original literal, avoiding binary-float rounding in algebra.
            literal = ast.get_source_segment(text, n)
            if 'e' in literal.lower() and abs(int(literal.lower().split('e')[1])) > 100:
                raise ValueError('exponent too large')
            value = Fraction(literal)
            if value.numerator.bit_length() > 512 or value.denominator.bit_length() > 512:
                raise ValueError('number too large')
            return clean({(): value}), ONE
        if isinstance(n, ast.Name) and n.id in allowed:
            return {(n.id,): Fraction(1)}, ONE
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            a, b = walk(n.operand)
            return ({k: -v for k, v in a.items()} if isinstance(n.op, ast.USub) else a), b
        if isinstance(n, ast.BinOp):
            a, b = walk(n.left)
            if isinstance(n.op, ast.Pow):
                if not isinstance(n.right, ast.Constant) or type(n.right.value) is not int or not 0 <= n.right.value <= 4:
                    raise ValueError('only powers 0..4 allowed')
                x, y = ONE, ONE
                for _ in range(n.right.value):
                    x, y = mul(x, a), mul(y, b)
                return x, y
            c, d = walk(n.right)
            if isinstance(n.op, ast.Add):
                return add(mul(a, d), mul(c, b)), mul(b, d)
            if isinstance(n.op, ast.Sub):
                return add(mul(a, d), mul(c, b), -1), mul(b, d)
            if isinstance(n.op, ast.Mult):
                return mul(a, c), mul(b, d)
            if isinstance(n.op, ast.Div):
                if not c:
                    raise ValueError('division by zero')
                # Only declared strictly positive financial denominators may
                # occur symbolically; never cancel a policy-domain pole.
                if set(c) != {()} and not all(
                    set(mon) <= {'V', 'equity', 'loans'} and coef > 0
                    for mon, coef in c.items()
                ):
                    raise ValueError('denominator is not certified positive')
                return mul(a, d), mul(b, c)
        raise ValueError('only declared names and arithmetic are allowed')

    return walk(tree.body)


def equivalent(actual, expected, symbols):
    a, b = parse(actual, set(symbols))
    c, d = parse(expected, set(symbols))
    return not add(mul(a, d), mul(c, b), -1)


def value(expression, values):
    a, b = parse(expression, set(values))

    def ev(p):
        total = Fraction(0)
        for names, coef in p.items():
            for name in names:
                coef *= Fraction(str(values[name]))
            total += coef
        return total

    return float(ev(a) / ev(b))


def polynomial_quotient(a, b):
    """Exact single-divisor long division, or None for a genuine rational form.

    Only call after parse(): removable policy-domain poles remain forbidden.
    Bounded graded-lex leading terms ensure deterministic termination.
    """
    if not b:
        raise ValueError('division by zero')
    variables = sorted({n for p in (a, b) for mon in p for n in mon})
    def order(mon):
        return (len(mon), tuple(mon.count(n) for n in variables))
    lead_b = max(b, key=order)
    remainder, quotient = dict(a), {}
    for _ in range(MAX_TERMS):
        if not remainder:
            return clean(quotient)
        lead_a = max(remainder, key=order)
        rest = list(lead_a)
        for n in lead_b:
            if n not in rest:
                return None
            rest.remove(n)
        mon = tuple(rest)
        coef = remainder[lead_a] / b[lead_b]
        quotient[mon] = quotient.get(mon, 0) + coef
        remainder = add(remainder, mul({mon: coef}, b), -1)
    raise ValueError('polynomial division too large')


def polynomial_text(p):
    terms = ['(' + str(coef) + ')' + ''.join('*' + x for x in mon)
             for mon, coef in sorted(p.items()) if coef]
    return '(' + ('+'.join(terms) or '0') + ')'


def substitute_polynomial(p, mapping):
    out = {}
    for mon, coef in p.items():
        rest = []
        for name in mon:
            if name in mapping:
                coef *= Fraction(str(mapping[name]))
            else:
                rest.append(name)
        key = tuple(rest)
        out[key] = out.get(key, 0) + coef
    return clean(out)


def substitute(expression, mapping):
    """Retain unknowns and certified-positive rational denominators exactly."""
    names = {n.id for n in ast.walk(ast.parse(expression, mode='eval')) if isinstance(n, ast.Name)}
    a, b = parse(expression, names)
    a, b = substitute_polynomial(a, mapping), substitute_polynomial(b, mapping)
    reduced = polynomial_quotient(a, b)
    if reduced is not None:
        return polynomial_text(reduced)
    return polynomial_text(a) + '/' + polynomial_text(b)
