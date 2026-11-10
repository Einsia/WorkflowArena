#!/usr/bin/env python3
"""Trim the tokio workspace so the carved crate has no registry twin.

    python3 trim_workspace.py /app

Two edits, both of them contamination fixes rather than housekeeping:

1. `Cargo.toml`: keep only the five crates the task needs -- the carved crate,
   its proc-macro crate, and the three downstream crates the regression set
   scores.  The internal members (benches, examples, stress-test, tests-build,
   tests-integration) carry dev-dependencies that pull `tokio` from crates.io.

2. `tokio/Cargo.toml`: drop the dev-dependencies that live behind a `cfg` or a
   target this image will never build for.  `mio-aio` is the one that matters --
   it is `cfg(target_os = "freebsd")` only and is requested with
   `features = ["tokio"]`, so it drags the registry `tokio` into the lock file,
   and `cargo vendor` resolves for *every* target regardless of what we compile.
   That is how a complete newer copy of the carved module ends up at
   /app/vendor/tokio-<newer>/src/sync, which is the answer sitting in the tree.

Removing them cannot change what gets built or scored: every one is unreachable
on x86_64-unknown-linux-gnu without `--cfg loom` or `--cfg tokio_unstable`, and
the loom models were removed with the carve anyway.
"""
import re
import sys
from pathlib import Path

KEEP = ["tokio", "tokio-macros", "tokio-test", "tokio-stream", "tokio-util"]

# dev-dependency tables that are unreachable for this image's target and cfgs
DROP_TABLES = [
    'target.\'cfg(target_os = "freebsd")\'.dev-dependencies',          # mio-aio -> registry tokio
    'target.\'cfg(all(target_family = "wasm", not(target_os = "wasi")))\'.dev-dependencies',
    "target.'cfg(loom)'.dev-dependencies",
    'target.\'cfg(all(tokio_unstable, target_has_atomic = "64"))\'.dev-dependencies',
]


def trim_members(path: Path) -> None:
    s = path.read_text()
    m = re.search(r"(?ms)^members = \[(.*?)^\]", s)
    if not m:
        raise SystemExit("workspace members block not found")
    members = re.findall(r'"([^"]+)"', m.group(1))
    missing = [k for k in KEEP if k not in members]
    if missing:
        raise SystemExit(f"expected members absent: {missing}")
    block = "members = [\n" + "".join(f'  "{x}",\n' for x in KEEP) + "]"
    path.write_text(s[: m.start()] + block + s[m.end():])
    print("workspace members kept:", KEEP)
    print("workspace members dropped:", sorted(set(members) - set(KEEP)))


def drop_tables(path: Path) -> None:
    s = path.read_text()
    for name in DROP_TABLES:
        pat = re.compile(r"(?ms)^\[" + re.escape(name) + r"\]\n.*?(?=^\[|\Z)")
        s, n = pat.subn("", s)
        print(f"  [{name}]: {'removed' if n else 'not present'}")
    path.write_text(s)
    left = re.findall(r"^\[(.*dev-dependencies)\]", s, re.M)
    print("dev-dependency tables remaining in tokio/Cargo.toml:", left)


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "/app")
    trim_members(root / "Cargo.toml")
    print("dropping unreachable dev-dependency tables:")
    drop_tables(root / "tokio" / "Cargo.toml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
