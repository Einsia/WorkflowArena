# Starting environment for wfa-carve-tokio-01.
#
# Source: tokio-rs/tokio tokio-1.49.0, fetched from codeload and verified against
# the SHA-256 pinned below in this Dockerfile.  The tarball carries no VCS
# history, so the removed implementation cannot be recovered with a checkout.
#
# Build needs the network.  The agent and the verifier run with no network, so
# every crate the workspace needs is vendored into the image and cargo is pointed
# at the vendor directory; `--offline` then works for the agent.
FROM rust:1.99.1-bookworm

ARG TOKIO_TAG=tokio-1.49.0
ARG TOKIO_DIR=tokio-tokio-1.49.0
ARG TOKIO_SHA256=e731bd44c3e8eb76b1e7fa052de3dcd477eae122fb4753b1fd00719b0ebd3eb5

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl jq python3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
RUN curl -sfL -o tokio.tgz \
        "https://codeload.github.com/tokio-rs/tokio/tar.gz/refs/tags/${TOKIO_TAG}" \
    && echo "${TOKIO_SHA256}  tokio.tgz" | sha256sum -c - \
    && tar xzf tokio.tgz \
    && mv "${TOKIO_DIR}" /app \
    && rm -rf /build

ENV CARGO_TERM_COLOR=never CARGO_INCREMENTAL=0

# Trim the workspace to the five crates the task needs: the carved crate, its
# proc-macro crate, and the three downstream crates the regression set scores.
#
# This is not housekeeping, it is a contamination fix.  The internal members
# (benches, examples, stress-test, tests-build, tests-integration) carry
# dev-dependencies that pull `tokio` from crates.io -- that is why plain
# `-p tokio` is ambiguous in this workspace, it resolves to both 1.49.0 (the path
# member) and 1.54.1 (the registry crate).  Vendoring the full workspace would
# therefore place a complete, newer implementation of the carved module at
# /app/vendor/tokio-1.54.1/src/sync, which is the answer sitting in the tree.
# Dropping those members keeps the registry tokio out of the dependency graph.
COPY carve.sh stubgen_rust.py trim_workspace.py /carve/
WORKDIR /app
RUN python3 /carve/trim_workspace.py /app

# tokio ships no Cargo.lock (it is a library workspace), so the lock is generated
# here and frozen into the image: without it the dependency versions would differ
# between this build and any later one.
RUN mkdir -p /app/.cargo \
    && cargo generate-lockfile \
    && cargo vendor --versioned-dirs /app/vendor > /app/.cargo/config.toml \
    && printf '\n[net]\noffline = true\n' >> /app/.cargo/config.toml

# Belt and braces. `cargo vendor` resolves for every target and cfg, so a
# registry copy of `tokio` can still reach the vendor tree through a path the
# trim above did not foresee. Any that does gets the same treatment as the real
# carve: its sync module is hollowed out, so the vendored crate still compiles if
# something genuinely needs it but contains no implementation to copy. The
# per-crate checksum file has to be blanked afterwards or cargo rejects the
# modified source.
RUN set -eu; \
    for d in /app/vendor/tokio-*/; do \
        [ -d "$d" ] || continue; \
        echo "neutralising vendored $d"; \
        [ -d "${d}src/sync" ] && python3 -I /carve/stubgen_rust.py --drop-test-mods \
            $(find "${d}src/sync" -name '*.rs'); \
        printf '{"files":{},"package":null}\n' > "${d}.cargo-checksum.json"; \
        rm -rf "${d}tests" "${d}benches" "${d}examples"; \
    done; \
    echo "done"

# Fail the build -- not the grading run -- if a readable copy of the carved
# implementation is still in the image.
#
# Scoped to vendored crates actually named `tokio*`, which is where the risk is.
# An earlier version grepped the whole vendor tree for a distinctive body line
# (`self.waiters.lock()`) and tripped on an unrelated crate: that is an ordinary
# Rust idiom, not evidence of a leak, and a check that cries wolf is worse than
# no check. The version-independent proof is the `todo!()` count: a hollowed copy
# has hundreds and no real bodies.
RUN set -eu; \
    echo "vendored crates: $(ls /app/vendor | wc -l)"; \
    ls -d /app/vendor/tokio* 2>/dev/null || echo "  no vendored crate named tokio*"; \
    for d in /app/vendor/tokio*/src/sync; do \
        [ -d "$d" ] || continue; \
        n=$(grep -ro 'todo!()' "$d" | wc -l); \
        echo "vendored sync at $d: $n hollowed bodies"; \
        [ "$n" -gt 100 ] || { echo "LEAK: $d was not hollowed"; exit 1; }; \
        if grep -rqF 'self.waiters.lock()' "$d"; then \
            echo "LEAK: real implementation body still in $d"; \
            grep -rlF 'self.waiters.lock()' "$d"; exit 1; \
        fi; \
    done; \
    echo "no readable copy of the carved implementation under /app/vendor"

RUN bash /carve/carve.sh /app

# Warm the build cache so the agent's first compile is not a cold one, and so the
# image itself proves the carved tree compiles and that the vendored sources are
# sufficient without the network.
RUN cargo build -p tokio@1.49.0 --features full --offline \
    && cargo build -p tokio-util -p tokio-stream -p tokio-test --all-features --offline

RUN test ! -d /app/.git \
    && test ! -d /app/tokio/src/sync/tests \
    && test ! -f /app/tokio/tests/sync_mpsc.rs \
    && test -f /app/tokio/tests/support/panic.rs \
    && grep -q 'todo!()' /app/tokio/src/sync/mutex.rs

WORKDIR /app
