# Starting environment for wfa-carve-nushell-01.
#
# Source: nushell/nushell 0.116.1, fetched from codeload and verified against
# the SHA-256 pinned below in this Dockerfile.  The tarball carries no VCS
# history, so the removed implementation cannot be recovered with a checkout,
# and `cargo vendor` puts only this workspace's third-party dependencies into
# /app/vendor -- nushell's own crates are never fetched from a registry, they
# are path dependencies inside the tree.
#
# Toolchain: 1.96.1, the channel in the repository's own rust-toolchain.toml.
#
# Build needs the network.  The agent and the verifier run with no network,
# which is why the dependency tree is vendored and the build cache is warmed
# during the build.
FROM rust:1.96.1-bookworm

ARG NU_TAG=0.116.1
ARG NU_DIR=nushell-0.116.1
ARG NU_SHA256=0cca0c5bc9d9eb608dee00c75b6b511917df6e66c784b034468bab2ff0fbb9b4

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl git jq python3 pkg-config libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
RUN curl -sfL -o nu.tgz \
        "https://codeload.github.com/nushell/nushell/tar.gz/refs/tags/${NU_TAG}" \
    && echo "${NU_SHA256}  nu.tgz" | sha256sum -c - \
    && tar xzf nu.tgz \
    && mv "${NU_DIR}" /app \
    && rm -rf /build

ENV CARGO_TERM_COLOR=never CARGO_INCREMENTAL=0
# Cap build parallelism: on a many-core build host cargo spawns one rustc per
# core and the build dies with "Too many open files (os error 24)" before the
# tree is ever compiled.  Observed on a 256-core node; 8 is plenty and keeps the
# image reproducible on big and small builders alike.
ENV CARGO_BUILD_JOBS=8
# debuginfo is the majority of a nushell debug build's disk and link time, and
# nothing the verifier measures depends on it.
ENV CARGO_PROFILE_DEV_DEBUG=0 CARGO_PROFILE_TEST_DEBUG=0

ENV CARGO_HTTP_MULTIPLEXING=false CARGO_HTTP_TIMEOUT=600 CARGO_NET_RETRY=10

COPY carve.sh stubgen_rs.py /carve/
RUN bash /carve/carve.sh /app

# The carved tree's own test binaries are already linked by carve.sh.  Warm the
# dependency build for the suite the verifier restores as well, so the agent's
# first compile is not a cold one.  It cannot be fully warmed: the test sources
# themselves do not exist yet.
RUN cd /app && cargo build --offline --locked --workspace --tests || true

# A login shell sources /etc/profile and resets PATH, which drops the base
# image's /usr/local/cargo/bin -- the verifier then reports `cargo: command not
# found` for every test and scores the reference solution 0. tests/config.json
# uses `bash -c`; this makes the toolchain survive a login shell regardless.
RUN printf 'export PATH=/usr/local/cargo/bin:/usr/local/rustup/bin:$PATH\n' \
        > /etc/profile.d/rust.sh

# Timestamp reference for the verifier's "what did the agent touch" evidence.
# Outside /app so the agent cannot remove it.
RUN touch /opt/task-start-marker

WORKDIR /app
ENV CARGO_NET_OFFLINE=true
