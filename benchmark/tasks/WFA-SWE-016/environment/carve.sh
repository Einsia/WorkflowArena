#!/bin/bash
# Materialise the starting tree: remove tokio's synchronisation primitives,
# keep their contract.
#
# Run during image build against a pristine source tree ($1).  Three things
# happen, in this order:
#
#   1. the 27 files under tokio/src/sync are hollowed out -- every declaration
#      stays (types, fields, signatures, trait impls, generics, `const` and
#      `static` items with their initialisers), every function body becomes
#      `todo!()`
#   2. the white-box tests are removed.  In Rust these live *inside* the carved
#      code -- `#[cfg(test)] mod tests` blocks in broadcast.rs and watch.rs, and
#      the `tokio/src/sync/tests/` directory behind `mod tests;` in sync/mod.rs.
#      They pin the removed internals (the batch semaphore's waiter list, the
#      loom models), so they cannot judge a reimplementation that picks its own
#      internals, and they would not compile against hollowed bodies.
#   3. the judging tests are removed: tokio/tests/sync_*.rs, 18 integration-test
#      binaries that link tokio as an external crate and therefore only touch the
#      public contract.  The verifier restores them after the agent finishes.
#
# `todo!()` rather than a synthesised zero value: `todo!()` has type `!`, which
# coerces to anything, so it satisfies the signature whatever the return type,
# lifetimes and borrows included.  It panics when called, which is safe here
# only because nothing in tokio/src initialises at load time by calling into
# `tokio::sync` -- verified: no `const`/`static` item in the crate is built from
# a carved function, and the `Mutex::const_new` call sites under
# tokio/src/{loom,process,util} resolve to the `crate::loom::std` shim instead.
# This is the hazard the Go carve-outs hit from the other side, where a panicking
# stub killed package init and the negative control read as "did not run".
#
# tokio/tests/support/{mpsc_stream,panic}.rs are NOT removed: seven tests that
# stay in the tree use them too.  They are also shipped in tests/hidden/ so the
# verifier restores known-good copies over whatever the agent left behind.
set -euo pipefail
TREE=${1:?usage: carve.sh <source-tree>}
HERE=$(cd "$(dirname "$0")" && pwd)

CARVE_FILES="tokio/src/sync/barrier.rs tokio/src/sync/batch_semaphore.rs
tokio/src/sync/broadcast.rs tokio/src/sync/mod.rs tokio/src/sync/mpsc/block.rs
tokio/src/sync/mpsc/bounded.rs tokio/src/sync/mpsc/chan.rs tokio/src/sync/mpsc/error.rs
tokio/src/sync/mpsc/list.rs tokio/src/sync/mpsc/mod.rs tokio/src/sync/mpsc/unbounded.rs
tokio/src/sync/mutex.rs tokio/src/sync/notify.rs tokio/src/sync/once_cell.rs
tokio/src/sync/oneshot.rs tokio/src/sync/rwlock.rs tokio/src/sync/rwlock/owned_read_guard.rs
tokio/src/sync/rwlock/owned_write_guard.rs tokio/src/sync/rwlock/owned_write_guard_mapped.rs
tokio/src/sync/rwlock/read_guard.rs tokio/src/sync/rwlock/write_guard.rs
tokio/src/sync/rwlock/write_guard_mapped.rs tokio/src/sync/semaphore.rs
tokio/src/sync/set_once.rs tokio/src/sync/task/atomic_waker.rs tokio/src/sync/task/mod.rs
tokio/src/sync/watch.rs"

HIDDEN_TARGETS="sync_barrier sync_broadcast sync_broadcast_weak sync_errors sync_mpsc
sync_mpsc_weak sync_mutex sync_mutex_owned sync_notify sync_notify_owned sync_once_cell
sync_oneshot sync_panic sync_rwlock sync_semaphore sync_semaphore_owned sync_set_once
sync_watch"

cd "$TREE"

echo "[carve] removing the white-box tests (they live inside the carved code)"
rm -rf tokio/src/sync/tests

echo "[carve] hollowing out the synchronisation primitives"
python3 -I "$HERE/stubgen_rust.py" --drop-test-mods $CARVE_FILES

echo "[carve] removing the judging tests"
for t in $HIDDEN_TARGETS; do rm -f "tokio/tests/$t.rs"; done
test ! -f tokio/tests/sync_mpsc.rs
# these two are shared with tests that stay, and must survive
test -f tokio/tests/support/mpsc_stream.rs
test -f tokio/tests/support/panic.rs

echo "[carve] no VCS history in the tree (a checkout would undo the carve)"
rm -rf .git
test ! -d .git

echo "[carve] the carved tree must still compile"
cargo build -p tokio@1.49.0 --features full --offline
echo "[carve] done"
