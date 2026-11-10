#!/usr/bin/env python3
"""Hollow out Rust function bodies in place, keeping every declaration.

    python3 -I stubgen_rust.py file.rs [file.rs ...]

What stays: modules, `use`, types, struct/enum/union definitions and all their
fields, trait definitions, `impl` blocks and their headers, generics, where
clauses, associated types, attributes, doc comments, and -- critically -- every
`const` and `static` item together with its initialiser.  Nothing in a
const-evaluated position is touched, so the crate cannot fail to compile with
"evaluation of constant panicked".

What goes: the body of every `fn` item, replaced by `todo!()`.  `todo!()` has
type `!`, which coerces to any type, so a hollowed body type-checks whatever
the signature promises -- including borrowed return types, `impl Trait`,
lifetimes and `async fn`.  That is the one place where Rust is easier to carve
than Go: there is no need to synthesise a zero value per return type, and no
need for a borrow-checker-pleasing dummy binding.

`todo!()` panics at run time.  That is safe here only because this crate has no
module-level initialisation that calls into the carved code (checked: no `const`
or `static` item in tokio/src is initialised from `tokio::sync`, and the
`Mutex::const_new` call sites in `tokio/src/{process,loom,util}` resolve to the
`crate::loom::std` shim, not to `crate::sync::Mutex`).  A panicking stub in a
tree that *does* initialise at load time kills the whole test binary and the
negative control then reads as "did not run" instead of "ran and failed".

`#[cfg(test)]`/`#[cfg(loom)]` `mod tests` items are deleted outright with
`--drop-test-mods`: in Rust the unit tests live inside the files being carved,
so they disappear along with the implementation and cannot judge anything.  The
declaration has to go too, or the crate stops compiling once the directory
behind `mod tests;` is removed.

The scanner is a hand-rolled lexer rather than a regex pass: Rust string, raw
string, byte string, char and lifetime literals and nested block comments all
contain braces and the token `fn`, and a regex cannot tell those from code.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def code_mask(src: str) -> bytearray:
    """1 for every byte of `src` that is real code, 0 inside comments/literals.

    Handles: `//` line comments, `/* */` block comments (nested, as Rust
    allows), `"..."`, `b"..."`, `r"..."`, `r#"..."#` / `br##"..."##`, and `'c'`
    char literals -- distinguished from lifetimes (`'a`), which are code.
    """
    n = len(src)
    mask = bytearray(b"\x01" * n)
    i = 0
    while i < n:
        c = src[i]

        if c == "/" and i + 1 < n and src[i + 1] == "/":
            j = src.find("\n", i)
            j = n if j < 0 else j
            mask[i:j] = b"\x00" * (j - i)
            i = j
            continue

        if c == "/" and i + 1 < n and src[i + 1] == "*":
            depth, j = 1, i + 2
            while j < n and depth:
                if src.startswith("/*", j):
                    depth += 1
                    j += 2
                elif src.startswith("*/", j):
                    depth -= 1
                    j += 2
                else:
                    j += 1
            mask[i:j] = b"\x00" * (j - i)
            i = j
            continue

        # raw string: optional b/c prefix, r, then #* then "
        m = re.match(r'(?:b|c)?r(#*)"', src[i:])
        if m and (i == 0 or not IDENT.match(src[i - 1])):
            hashes = m.group(1)
            close = '"' + hashes
            j = src.find(close, i + m.end())
            j = n if j < 0 else j + len(close)
            mask[i:j] = b"\x00" * (j - i)
            i = j
            continue

        if c == '"' or (c in "bc" and i + 1 < n and src[i + 1] == '"'):
            j = i + (1 if c == '"' else 2)
            while j < n:
                if src[j] == "\\":
                    j += 2
                    continue
                if src[j] == '"':
                    j += 1
                    break
                j += 1
            mask[i:j] = b"\x00" * (j - i)
            i = j
            continue

        if c == "'":
            # `'\n'`, `'a'`, `'\u{1}'` are literals; `'a` followed by anything
            # that is not a closing quote is a lifetime and stays code.
            if src.startswith("'\\", i):
                j = i + 2
                while j < n and src[j] != "'":
                    j += 1
                j = min(j + 1, n)
                mask[i:j] = b"\x00" * (j - i)
                i = j
                continue
            if i + 2 < n and src[i + 2] == "'":
                mask[i : i + 3] = b"\x00\x00\x00"
                i += 3
                continue
            i += 1  # lifetime
            continue

        i += 1
    return mask


def find_code(src: str, mask: bytearray, pat: re.Pattern, start: int):
    """Next match of `pat` that begins on a code byte."""
    pos = start
    while True:
        m = pat.search(src, pos)
        if not m:
            return None
        if mask[m.start()]:
            return m
        pos = m.start() + 1


def match_brace(src: str, mask: bytearray, open_idx: int) -> int:
    """Index just past the `}` closing the `{` at `open_idx`."""
    depth, i, n = 0, open_idx, len(src)
    while i < n:
        if mask[i]:
            if src[i] == "{":
                depth += 1
            elif src[i] == "}":
                depth -= 1
                if depth == 0:
                    return i + 1
        i += 1
    raise ValueError(f"unbalanced brace at offset {open_idx}")


def body_start(src: str, mask: bytearray, after_name: int):
    """Offset of the `{` opening a fn body, or None if the fn has no body.

    Scans forward keeping `()` and `[]` depth so that a `{` inside a const
    generic argument or a tuple does not get mistaken for the body.  A `;` at
    depth zero means this is a trait method declaration, which has no body and
    must be left exactly as it is.
    """
    paren = brack = 0
    i, n = after_name, len(src)
    while i < n:
        if mask[i]:
            c = src[i]
            if c == "(":
                paren += 1
            elif c == ")":
                paren -= 1
            elif c == "[":
                brack += 1
            elif c == "]":
                brack -= 1
            elif paren == 0 and brack == 0:
                if c == "{":
                    return i
                if c == ";":
                    return None
        i += 1
    return None


# Attributes, whitespace and doc comments that belong to the item that follows.
# The doc comment has to be swallowed with the item: a `///` left with nothing
# after it is a hard error ("expected item after doc comment"), not a warning.
ATTR_OR_WS = re.compile(r"(?:[ \t]*///[^\n]*\n|\s|#\[[^\]]*\]|#!\[[^\]]*\])*\Z")
TEST_CFG = re.compile(r"#\[(?:cfg|cfg_attr)\s*\(\s*(?:all\s*\(\s*)?(?:test|loom)\b")


def drop_test_mods(src: str) -> tuple[str, int]:
    """Delete `#[cfg(test)] mod tests { ... }` and `#[cfg(test)] mod tests;`."""
    pat = re.compile(r"^(?P<indent>[ \t]*)mod\s+(?P<name>tests?)\s*(?P<tail>[{;])", re.M)
    dropped = 0
    while True:
        mask = code_mask(src)
        m = find_code(src, mask, pat, 0)
        hit = None
        while m:
            # look back over attributes/whitespace for a test/loom cfg gate
            head = src[max(0, m.start() - 400) : m.start()]
            attrs = ATTR_OR_WS.search(head).group(0)
            if TEST_CFG.search(attrs):
                hit = (m, m.start() - len(attrs))
                break
            m = find_code(src, mask, pat, m.end())
        if not hit:
            return src, dropped
        m, cut = hit
        if m.group("tail") == "{":
            end = match_brace(src, mask, src.index("{", m.start("tail")))
        else:
            end = m.end()
        src = src[:cut] + src[end:]
        dropped += 1


MACRO_CALL = re.compile(r"\b(?P<name>[a-z_][a-z0-9_]*)\s*!\s*(?P<open>[({\[])")
CLOSERS = {"(": ")", "[": "]", "{": "}"}

# A macro invocation's token tree is *not* code: the macro defines its own
# grammar, so rewriting tokens inside it can produce something the rules no
# longer match.  tokio hits this for real: `generate_addr_of_methods!` matches
# the function body literally --
#
#     unsafe fn addr_of_pointers(self: NonNull<Self>) -> NonNull<...> {
#         &self.pointers
#     }
#
# -- so replacing that body with `todo!()` is a *compile* error
# ("no rules expected `todo`"), not a semantic one.  Macro bodies are therefore
# opaque by default.
#
# The exception is the `cfg_*!` family in tokio/src/macros/cfg.rs, every member
# of which is declared `($($item:item)*) => { ... $item ... }`: it takes whole
# items and re-emits them behind a `#[cfg]`, so a hollowed body inside one is
# still a well-formed item.  Those have to stay carvable -- four real method
# bodies in tokio/src/sync live inside `cfg_time!` / `cfg_process_driver!`.
PASSTHROUGH = re.compile(r"^cfg_[a-z0-9_]*$")


def token_tree_end(src: str, mask: bytearray, open_idx: int):
    """Index just past the delimiter matching the one at `open_idx`."""
    opener = src[open_idx]
    closer = CLOSERS[opener]
    depth, i, n = 0, open_idx, len(src)
    while i < n:
        if mask[i]:
            if src[i] == opener:
                depth += 1
            elif src[i] == closer:
                depth -= 1
                if depth == 0:
                    return i + 1
        i += 1
    return None


def opaque_macro_spans(src: str, mask: bytearray, passthrough=PASSTHROUGH):
    """Spans of macro invocations whose contents must not be rewritten."""
    spans = []
    i = 0
    while True:
        m = find_code(src, mask, MACRO_CALL, i)
        if not m:
            return spans
        o = m.start("open")
        end = token_tree_end(src, mask, o)
        if end is None:
            return spans
        if not passthrough.match(m.group("name")):
            spans.append((m.start(), end))
            i = end            # nested invocations are already covered
        else:
            i = m.end()        # descend into a `$item`-taking macro


def hollow(src: str, stub: str = "todo!()") -> tuple[str, int]:
    """Replace every `fn` item body with `stub`, skipping macro token trees.

    Returns (text, bodies_hollowed, bodies_skipped_in_macros).
    """
    fn_pat = re.compile(r"\bfn\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)")
    i = 0
    count = 0
    skipped = 0
    while True:
        mask = code_mask(src)  # recomputed per edit: offsets shift
        spans = opaque_macro_spans(src, mask)
        m = find_code(src, mask, fn_pat, i)
        if not m:
            break
        b = body_start(src, mask, m.end())
        if b is None:                       # trait method declaration, no body
            i = m.end()
            continue
        inside = next((s for s in spans if s[0] <= b < s[1]), None)
        if inside is not None:
            skipped += 1
            i = inside[1]                   # jump past the whole invocation
            continue
        end = match_brace(src, mask, b)
        replacement = "{ " + stub + " }"
        src = src[:b] + replacement + src[end:]
        i = b + len(replacement)
        count += 1
    return src, count, skipped


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--stub", default="todo!()")
    ap.add_argument("--drop-test-mods", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    total_fns = total_mods = total_skipped = 0
    for path in a.files:
        src = original = path.read_text()
        mods = 0
        if a.drop_test_mods:
            src, mods = drop_test_mods(src)
        src, fns, skipped = hollow(src, a.stub)
        before = original.count("\n") + 1
        after = src.count("\n") + 1
        note = f", {skipped} left in macros" if skipped else ""
        print(f"  {path}: {fns} fn bodies, {mods} test mods{note}, "
              f"{before} -> {after} lines")
        total_fns += fns
        total_mods += mods
        total_skipped += skipped
        if not a.dry_run and src != original:
            path.write_text(src)
    print(f"[stubgen_rust] {total_fns} fn bodies hollowed, {total_mods} test mods dropped, "
          f"{total_skipped} bodies left intact inside opaque macro invocations")
    if total_fns == 0:
        print("[stubgen_rust] REFUSED: nothing was carved", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
