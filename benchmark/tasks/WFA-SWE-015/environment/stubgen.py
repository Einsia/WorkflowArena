#!/usr/bin/env python3
"""Hollow out Python function bodies in place, keeping the whole contract.

The Go equivalent (`stubgen.go`) rewrites every function body to "declare the
zero values and return them".  This is the same idea for Python:

  * every `def` / `async def` at module level or in a class body keeps its
    decorators, its signature, its type annotations and its docstring
  * the executable part of the body is replaced by a single return of a zero
    value **derived from the return annotation** (`dict[...]` -> `{}`,
    `bool` -> `False`, ...), falling back to `None`
  * a function that used `yield` stays a generator (`yield from ()`), because
    callers iterate over it and `None` is not iterable
  * every module-level and class-level assignment is left untouched, so
    constants, registries and `ClassVar` tables survive

Zero values rather than `raise NotImplementedError`: this tree runs carved code
during import (`_COERCES_TO = _build_coerces_to()` in annotate_types, and
`GEN_DISPATCH = _build_gen_dispatch()` in simplify), and downstream modules read
those tables in their own class bodies (`sqlglot/dialects/bigquery.py` does
`{**TypeAnnotator.COERCES_TO, ...}`).  A raising stub would abort the import of
`sqlglot` itself and the negative control would read as "nothing ran" instead of
"everything failed".  A typed zero value keeps the package importable.

Bodies that are already `...` or `pass` (`@overload` declarations, `Protocol`
methods) are left exactly as they are.

    python3 -I stubgen.py <file.py> [<file.py> ...]

Prints one line per file: how many functions were hollowed out.
"""

from __future__ import annotations

import ast
import sys

# Return-annotation text (as produced by ast.unparse) -> zero-value expression.
# Matched on the outermost name, so `dict[str, int]` and `t.Dict[str, int]`
# both land on `{}`.
_CONTAINER_ZERO = {
    "dict": "{}",
    "Dict": "{}",
    "defaultdict": "{}",
    "DefaultDict": "{}",
    "Mapping": "{}",
    "MutableMapping": "{}",
    "OrderedDict": "{}",
    "Counter": "{}",
    "list": "[]",
    "List": "[]",
    "Sequence": "[]",
    "MutableSequence": "[]",
    "set": "set()",
    "Set": "set()",
    "frozenset": "frozenset()",
    "FrozenSet": "frozenset()",
    "AbstractSet": "set()",
    "tuple": "()",
    "Tuple": "()",
    "bool": "False",
    "int": "0",
    "float": "0.0",
    "complex": "0j",
    "str": '""',
    "bytes": 'b""',
}

# Annotations that mean "this function is iterated over".  A plain `return None`
# stub for one of these breaks the caller rather than the callee.
_ITERATOR_ANNOTATIONS = {
    "Iterator",
    "Iterable",
    "Generator",
    "AsyncIterator",
    "AsyncIterable",
    "AsyncGenerator",
}


def _head(annotation: str) -> str:
    """Outermost name of an annotation: `t.Dict[str, int]` -> `Dict`."""
    text = annotation.strip()
    if text.startswith("'") or text.startswith('"'):
        text = text.strip("'\"").strip()
    bracket = text.find("[")
    if bracket != -1:
        text = text[:bracket]
    return text.rsplit(".", 1)[-1].strip()


def _is_optional(annotation: str) -> bool:
    text = annotation.strip().strip("'\"")
    if text.startswith("Optional[") or text.endswith(".Optional") or "Optional[" in text:
        return True
    # `X | None` only counts at the top level, which is where it ever appears here.
    depth = 0
    for i, ch in enumerate(text):
        if ch in "[(":
            depth += 1
        elif ch in "])":
            depth -= 1
        elif ch == "|" and depth == 0:
            parts = [p.strip() for p in text.split("|")]
            return "None" in parts
    return False


def type_aliases(tree: ast.Module) -> dict[str, str]:
    """Module-level type aliases, so `-> BinaryCoercions` can resolve to a dict.

    `annotate_types.swap_all` is annotated with an alias, and its result is
    splatted into a class-level table during import; a `None` stub there kills
    the import of `sqlglot` itself.
    """
    out: dict[str, str] = {}

    def record(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.If):  # `if t.TYPE_CHECKING:` blocks
                record(child)
            elif isinstance(child, ast.Assign) and len(child.targets) == 1:
                target = child.targets[0]
                if isinstance(target, ast.Name):
                    out.setdefault(target.id, ast.unparse(child.value))
            elif isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
                if child.value is not None:
                    out.setdefault(child.target.id, ast.unparse(child.value))
            elif child.__class__.__name__ == "TypeAlias":  # PEP 695 `type X = ...`
                name = getattr(child, "name", None)
                if isinstance(name, ast.Name):
                    out.setdefault(name.id, ast.unparse(child.value))

    record(tree)
    return out


def zero_value(
    func: ast.FunctionDef | ast.AsyncFunctionDef, aliases: dict[str, str] | None = None
) -> str:
    """The statement that replaces the body."""
    if _uses_yield(func):
        # Keep it a generator that yields nothing.
        return "yield from ()"

    if func.returns is None:
        return "return None"

    annotation = ast.unparse(func.returns)
    head = _head(annotation)

    # Follow type aliases until something recognisable turns up.
    for _ in range(5):
        if head in _CONTAINER_ZERO or head in _ITERATOR_ANNOTATIONS:
            break
        resolved = (aliases or {}).get(head)
        if resolved is None or _head(resolved) == head:
            break
        annotation = resolved
        head = _head(annotation)

    if head in _ITERATOR_ANNOTATIONS:
        return "return iter(())"
    if _is_optional(annotation):
        return "return None"
    return "return " + _CONTAINER_ZERO.get(head, "None")


def _uses_yield(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Does this function itself yield?  Nested function scopes do not count."""
    stack = list(func.body)
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.Yield, ast.YieldFrom)):
            return True
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue  # a different scope's yields belong to that scope
        stack.extend(ast.iter_child_nodes(node))
    return False


def _is_trivial_body(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """`...`, `pass`, or nothing but a docstring: already a declaration."""
    body = [s for s in func.body if not _is_docstring(s)]
    if not body:
        return True
    if len(body) > 1:
        return False
    stmt = body[0]
    if isinstance(stmt, ast.Pass):
        return True
    return (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Constant)
        and stmt.value.value is Ellipsis
    )


def _is_docstring(stmt: ast.stmt) -> bool:
    return (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Constant)
        and isinstance(stmt.value.value, str)
    )


def _collect(node: ast.AST, out: list) -> None:
    """Functions at module level and in class bodies, outermost first."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append(child)
            # Do not descend: nested defs go away with the body we replace.
        elif isinstance(child, ast.ClassDef):
            _collect(child, out)


def decorator_names(source: str) -> set[str]:
    """Bare names used in decorator position anywhere in `source`.

    A decorator (and a decorator factory even more so) runs while the class or
    module body is being executed, i.e. during import.  `simplify.catch` is used
    as `@catch(ModuleNotFoundError, UnsupportedUnit)` in a class body, so a
    hollowed `catch` makes `import sqlglot.optimizer.simplify` raise and the
    negative control degenerates into "nothing ran".  Those functions keep their
    bodies; they are plumbing, not the behaviour under test.
    """
    names: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        for dec in node.decorator_list:
            target = dec.func if isinstance(dec, ast.Call) else dec
            if isinstance(target, ast.Name):
                names.add(target.id)
    return names


def _called_names(nodes, cross_scopes: bool = True) -> set[str]:
    """Bare function names called anywhere under `nodes`.

    With `cross_scopes=False`, `lambda` and `def` bodies are skipped: the call
    inside them happens when the callable is invoked, not where it is written,
    so a lambda in a class-body table is not an import-time call.
    """
    names: set[str] = set()
    stack = list(nodes)
    while stack:
        node = stack.pop()
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            names.add(node.func.id)
        if not cross_scopes and isinstance(
            node, (ast.Lambda, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue
        stack.extend(ast.iter_child_nodes(node))
    return names


def import_time_calls(source: str) -> set[str]:
    """Names called while the module body or a class body executes.

    These run on `import`, before any solution code can be involved.  In this
    tree `_COERCES_TO = _build_coerces_to()` and `GEN_DISPATCH =
    _build_gen_dispatch()` are module-level, and downstream class bodies index
    into the result (`sqlglot/dialects/bigquery.py` does
    `COERCES_TO[exp.DType.DECIMAL] |= {...}`), so an empty-dict stub raises
    `KeyError` during `import sqlglot.dialects.bigquery`.  Nothing in the tree
    would run and the negative control would be meaningless.
    """
    names: set[str] = set()
    stack: list[ast.AST] = [ast.parse(source)]
    while stack:
        node = stack.pop()
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                continue  # deferred until called, not import time
            if isinstance(child, ast.ClassDef):
                stack.append(child)
                names |= _called_names(child.bases + child.keywords, cross_scopes=False)
                continue
            names |= _called_names([child], cross_scopes=False)
    return names


def call_graph(source: str) -> dict[str, set[str]]:
    """Top-level / method name -> bare names it calls."""
    tree = ast.parse(source)
    funcs: list = []
    _collect(tree, funcs)
    return {f.name: _called_names(f.body) for f in funcs}


def hollow(source: str, keep_names: frozenset[str] = frozenset()) -> tuple[str, int, list[str]]:
    lines = source.splitlines(keepends=True)
    tree = ast.parse(source)
    aliases = type_aliases(tree)

    funcs: list = []
    _collect(tree, funcs)

    # Rewrite from the bottom up so earlier line numbers stay valid.
    edits = []
    kept: list[str] = []
    for func in funcs:
        if _is_trivial_body(func):
            continue
        if func.name in keep_names:
            kept.append(func.name)
            continue
        keep = [s for s in func.body if _is_docstring(s)][:1]
        first = func.body[0]
        # A decorated nested def starts at its first decorator, not at `def`.
        first_line = min(
            [first.lineno] + [d.lineno for d in getattr(first, "decorator_list", [])]
        )
        last_line = max(
            getattr(s, "end_lineno", s.lineno) for s in ast.walk(func) if hasattr(s, "lineno")
        )
        indent = " " * first.col_offset

        replacement = ""
        header_prefix = lines[first_line - 1][: first.col_offset]
        if header_prefix.strip():
            # `def f() -> int: return 1` — the signature shares the line.
            replacement += header_prefix.rstrip() + "\n"
            indent = " " * (func.col_offset + 4)

        if keep:
            doc = keep[0]
            replacement += "".join(lines[doc.lineno - 1 : doc.end_lineno])
        replacement += f"{indent}{zero_value(func, aliases)}\n"

        edits.append((first_line - 1, last_line, replacement))

    edits.sort(key=lambda e: e[0], reverse=True)
    for start, end, replacement in edits:
        lines[start:end] = [replacement]

    return "".join(lines), len(edits), kept


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2

    sources = {}
    for path in argv:
        with open(path, encoding="utf-8") as fh:
            sources[path] = fh.read()

    # Two kinds of body have to survive, or the package stops importing:
    #   * decorators and decorator factories, which run at class/module body time
    #   * functions called directly from a module or class body
    # plus whatever those call in turn.
    seeds: set[str] = set()
    graph: dict[str, set[str]] = {}
    for src in sources.values():
        seeds |= decorator_names(src)
        seeds |= import_time_calls(src)
        for name, callees in call_graph(src).items():
            graph.setdefault(name, set()).update(callees)

    keep: set[str] = set()
    todo = [n for n in seeds if n in graph]
    while todo:
        name = todo.pop()
        if name in keep:
            continue
        keep.add(name)
        todo += [c for c in graph.get(name, ()) if c in graph and c not in keep]
    keep_names = frozenset(keep)

    total = 0
    all_kept: list[str] = []
    for path in argv:
        source = sources[path]
        out, n, kept = hollow(source, keep_names)
        # Must still be syntactically valid; fail loudly if not.
        ast.parse(out)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(out)
        before = len(source.splitlines())
        after = len(out.splitlines())
        total += n
        all_kept += kept
        print(f"  {path}: {n} functions hollowed, {before} -> {after} lines")
    print(f"  total: {total} functions hollowed in {len(argv)} files")
    if all_kept:
        print(f"  kept (used as decorators, run at import): {sorted(set(all_kept))}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
