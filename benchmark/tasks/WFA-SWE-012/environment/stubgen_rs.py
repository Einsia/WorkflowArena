#!/usr/bin/env python3
"""Hollow out Rust function bodies, keeping the whole contract.

The Rust counterpart of `stubgen.go`.  What survives is everything a compiler
and a reader need in order to know *what* the subsystem is: `struct`, `enum`,
`type`, `trait` and `impl` headers with their items, every `fn` signature
(including generics, lifetimes and `where` clauses), every `const`, `static`,
`thread_local!` and `macro_rules!` definition, every attribute, and every doc
comment.  What disappears is every `fn` body, i.e. the algorithm.

A removed body becomes `todo!()`.  Unlike Go, Rust has no package-level
initialisation that could call a carved function, so a panicking body cannot
stop the test binary from starting; `const`/`static` initialisers *are*
const-evaluated, which is why this tool never touches them.  Two cases still
need a real value instead of a divergence, and both are handled by
`--overrides`:

  * `-> impl Trait` — the hidden type of an opaque return cannot be inferred
    from `!`, so `todo!()` does not type-check.
  * anything else the type checker rejects; the override table is the single
    documented place where a carve spec admits that.

Inline `#[cfg(test)]` items are *deleted*, not hollowed: an inline test is part
of the implementation file, so it cannot judge a re-implementation.  They have
to be deleted from the reference tree as well, which is why `--mode
strip-tests` exists: run it on both trees so the two sides run the same suite.

    python3 -I stubgen_rs.py --mode carve|strip-tests [--overrides o.json]
                             [--report r.json] FILE...

Override file shape (body text is inserted verbatim between braces):

    {"crates/x/src/y.rs": {"get_executable_files": "std::iter::empty()"}}

`--keep` names functions whose body stays as it is, same `file.rs::fn` syntax.
It exists for declarative metadata that *is* the contract rather than the
algorithm — a nu command's `name`/`signature` is the command line interface
itself, and it is read while the engine state is built, so hollowing it stops
the shell from starting at all rather than stopping completion from working.
"""
import argparse
import json
import re
import sys
from pathlib import Path

IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
OPEN = {"(": ")", "[": "]", "{": "}"}
CLOSE = {v: k for k, v in OPEN.items()}


class Scanner:
    """Character cursor that knows Rust's comments and literals."""

    def __init__(self, text):
        self.s = text
        self.n = len(text)

    def skip_trivia(self, i):
        """Advance over whitespace and comments."""
        while i < self.n:
            c = self.s[i]
            if c.isspace():
                i += 1
            elif self.s.startswith("//", i):
                j = self.s.find("\n", i)
                i = self.n if j < 0 else j + 1
            elif self.s.startswith("/*", i):
                i = self.skip_block_comment(i)
            else:
                break
        return i

    def skip_block_comment(self, i):
        depth = 0
        while i < self.n:
            if self.s.startswith("/*", i):
                depth += 1
                i += 2
            elif self.s.startswith("*/", i):
                depth -= 1
                i += 2
                if depth == 0:
                    return i
            else:
                i += 1
        return self.n

    def skip_literal(self, i):
        """If a string/char/byte/raw literal starts at `i`, return its end."""
        s, n = self.s, self.n
        j = i
        # prefixes: b, c, r, br, cr
        m = re.match(r'(?:b|c)?r(#*)"', s[j:j + 8])
        if m:
            hashes = m.group(1)
            j += m.end()
            term = '"' + hashes
            k = s.find(term, j)
            return n if k < 0 else k + len(term)
        m = re.match(r'(?:b|c)?"', s[j:j + 3])
        if m:
            j += m.end()
            while j < n:
                if s[j] == "\\":
                    j += 2
                elif s[j] == '"':
                    return j + 1
                else:
                    j += 1
            return n
        # char literal vs lifetime: 'a' is a char, 'a is a lifetime
        m = re.match(r"b?'(\\.|[^\\'])'", s[j:j + 12])
        if m:
            return j + m.end()
        return None

    def skip_token(self, i):
        """Advance exactly one token (or one char) past `i`."""
        e = self.skip_literal(i)
        if e is not None:
            return e
        m = IDENT.match(self.s, i)
        if m:
            return m.end()
        return i + 1

    def match_delim(self, i):
        """`i` is at an opening delimiter; return the index past its match."""
        assert self.s[i] in OPEN, self.s[i]
        stack = [self.s[i]]
        i += 1
        while i < self.n and stack:
            c = self.s[i]
            if c.isspace():
                i += 1
                continue
            if self.s.startswith("//", i) or self.s.startswith("/*", i):
                i = self.skip_trivia(i)
                continue
            e = self.skip_literal(i)
            if e is not None:
                i = e
                continue
            if c in OPEN:
                stack.append(c)
                i += 1
            elif c in CLOSE:
                if stack and stack[-1] == CLOSE[c]:
                    stack.pop()
                i += 1
            else:
                i = self.skip_token(i)
        return i

    def find_body(self, i):
        """From inside a `fn` signature at `i`, locate the body braces.

        Returns (open_brace, past_close_brace), or None for a bodiless `fn`
        (a trait method declaration).  A `{` can only start the body: inside a
        signature every other `{` is enclosed by `(`/`[`, and a where clause
        contains no braces.
        """
        depth = 0
        while i < self.n:
            c = self.s[i]
            if c.isspace():
                i += 1
                continue
            if self.s.startswith("//", i) or self.s.startswith("/*", i):
                i = self.skip_trivia(i)
                continue
            e = self.skip_literal(i)
            if e is not None:
                i = e
                continue
            if c in "([":
                depth += 1
                i += 1
            elif c in ")]":
                depth -= 1
                i += 1
            elif c == "{" and depth == 0:
                return i, self.match_delim(i)
            elif c == ";" and depth == 0:
                return None
            else:
                i = self.skip_token(i)
        return None


CFG_TEST = re.compile(r"^#!?\[\s*cfg(_attr)?\s*\(")


def is_cfg_test_attr(text):
    if not CFG_TEST.match(text):
        return False
    inner = text[text.index("(") + 1:]
    return bool(re.search(r"\btest\b", inner))


def process(text, path_key, carve, overrides, keep=None):
    sc = Scanner(text)
    keep = keep or set()
    edits = []
    stats = {"stubbed": [], "deleted_test_items": 0, "bodiless": 0, "overridden": [],
             "kept": []}
    i = 0
    pending_attr_start = None   # start of a run of attributes/doc comments

    while i < sc.n:
        c = text[i]
        if c.isspace():
            i += 1
            continue
        if text.startswith("//", i) or text.startswith("/*", i):
            if pending_attr_start is None:
                pending_attr_start = i
            i = sc.skip_trivia(i)
            continue

        e = sc.skip_literal(i)
        if e is not None:
            i = e
            pending_attr_start = None
            continue

        # attribute
        if c == "#" and text[i:i + 2] in ("#[", "#!"):
            j = text.index("[", i)
            end = sc.match_delim(j)
            attr = text[i:end]
            start = i if pending_attr_start is None else pending_attr_start
            if is_cfg_test_attr(attr):
                k = sc.skip_trivia(end)
                # skip any further attributes on the same item
                while k < sc.n and text[k] == "#":
                    k = sc.match_delim(text.index("[", k))
                    k = sc.skip_trivia(k)
                item_end = end_of_item(sc, k)
                if item_end is not None:
                    edits.append((start, item_end, ""))
                    stats["deleted_test_items"] += 1
                    i = item_end
                    pending_attr_start = None
                    continue
            if pending_attr_start is None:
                pending_attr_start = i
            i = end
            continue

        m = IDENT.match(text, i)
        if not m:
            i += 1
            pending_attr_start = None
            continue
        word = m.group(0)

        if word == "macro_rules":
            k = sc.skip_trivia(m.end())
            if k < sc.n and text[k] == "!":
                k = sc.skip_trivia(k + 1)
                k2 = IDENT.match(text, k)
                if k2:
                    k = sc.skip_trivia(k2.end())
                if k < sc.n and text[k] in OPEN:
                    i = sc.match_delim(k)   # leave the macro definition alone
                    pending_attr_start = None
                    continue
            i = m.end()
            continue

        if word == "fn":
            after = sc.skip_trivia(m.end())
            name_m = IDENT.match(text, after)
            if name_m is None:          # `fn(..) -> ..` function-pointer type
                i = m.end()
                continue
            name = name_m.group(0)
            body = sc.find_body(name_m.end())
            if body is None:
                stats["bodiless"] += 1
                i = name_m.end()
                pending_attr_start = None
                continue
            b0, b1 = body
            if carve and f"{path_key}::{name}" in keep:
                stats["kept"].append(name)
            elif carve:
                line_start = text.rfind("\n", 0, m.start()) + 1
                indent = re.match(r"[ \t]*", text[line_start:]).group(0)
                repl = overrides.get(path_key, {}).get(name)
                if repl is None:
                    repl = "todo!()"
                else:
                    stats["overridden"].append(name)
                new = f"{{\n{indent}    {repl}\n{indent}}}"
                edits.append((b0, b1, new))
                stats["stubbed"].append(name)
            i = b1
            pending_attr_start = None
            continue

        i = m.end()
        pending_attr_start = None

    out = []
    last = 0
    for a, b, new in edits:
        out.append(text[last:a])
        out.append(new)
        last = b
    out.append(text[last:])
    return "".join(out), stats


def code_brace_balance(text):
    """`{` minus `}` counting only real code: comments and literals carry both."""
    sc = Scanner(text)
    i, bal = 0, 0
    while i < sc.n:
        c = text[i]
        if c.isspace():
            i += 1
            continue
        if text.startswith("//", i) or text.startswith("/*", i):
            i = sc.skip_trivia(i)
            continue
        e = sc.skip_literal(i)
        if e is not None:
            i = e
            continue
        if c == "{":
            bal += 1
        elif c == "}":
            bal -= 1
        i = sc.skip_token(i)
    return bal


def end_of_item(sc, i):
    """End of the item starting at `i`: a braced body, or the next `;`."""
    depth = 0
    while i < sc.n:
        c = sc.s[i]
        if c.isspace():
            i += 1
            continue
        if sc.s.startswith("//", i) or sc.s.startswith("/*", i):
            i = sc.skip_trivia(i)
            continue
        e = sc.skip_literal(i)
        if e is not None:
            i = e
            continue
        if c == "{" and depth == 0:
            return sc.match_delim(i)
        if c in "([":
            depth += 1
            i += 1
        elif c in ")]":
            depth -= 1
            i += 1
        elif c == ";" and depth == 0:
            return i + 1
        else:
            i = sc.skip_token(i)
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=["carve", "strip-tests"], required=True)
    ap.add_argument("--overrides", type=Path, default=None)
    ap.add_argument("--keep", default="",
                    help="comma/space separated file.rs::fn whose body stays intact")
    ap.add_argument("--report", type=Path, default=None)
    ap.add_argument("files", nargs="+")
    a = ap.parse_args(argv)

    overrides = json.loads(a.overrides.read_text()) if a.overrides else {}
    keep = {k for k in re.split(r"[,\s]+", a.keep) if k}
    carve = a.mode == "carve"
    report = {}
    total_fns = total_del = 0
    kept_seen = set()
    for f in a.files:
        p = Path(f)
        text = p.read_text()
        new, stats = process(text, f, carve, overrides, keep)
        kept_seen |= {f"{f}::{n}" for n in stats["kept"]}
        if code_brace_balance(new) != code_brace_balance(text):
            print(f"stubgen_rs: brace balance changed in {f}", file=sys.stderr)
            return 2
        p.write_text(new)
        stats["lines_before"] = text.count("\n") + 1
        stats["lines_after"] = new.count("\n") + 1
        stats["stubbed_count"] = len(stats["stubbed"])
        report[f] = stats
        total_fns += len(stats["stubbed"])
        total_del += stats["deleted_test_items"]
        print(f"  {f}: {len(stats['stubbed'])} bodies hollowed, "
              f"{stats['deleted_test_items']} cfg(test) items deleted, "
              f"{stats['bodiless']} declarations left alone"
              + (f", overrides {stats['overridden']}" if stats["overridden"] else "")
              + (f", kept {stats['kept']}" if stats["kept"] else ""))

    if carve and keep - kept_seen:
        print(f"stubgen_rs: --keep entries never matched: {sorted(keep - kept_seen)}",
              file=sys.stderr)
        return 2

    unused = {k: sorted(set(v) - set(report.get(k, {}).get("overridden", [])))
              for k, v in overrides.items()}
    unused = {k: v for k, v in unused.items() if v}
    if carve and unused:
        print(f"stubgen_rs: override entries never applied: {unused}", file=sys.stderr)
        return 2

    print(f"stubgen_rs: {total_fns} bodies, {total_del} cfg(test) items, {len(a.files)} files")
    if a.report:
        a.report.write_text(json.dumps(report, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
