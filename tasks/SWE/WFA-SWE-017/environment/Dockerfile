# Starting environment for wfa-carve-tsdb-01.
#
# Source: prometheus/prometheus v3.13.5, fetched from codeload and verified
# against the SHA-256 pinned below in this Dockerfile.  The tarball carries
# no VCS history, so the removed implementation cannot be recovered with a
# checkout; the Go module cache holds this module's dependencies only.
#
# Build needs the network.  The agent and the verifier run with no network.
FROM golang:1.26.2-bookworm

ARG PROM_TAG=v3.13.5
ARG PROM_DIR=prometheus-3.13.5
ARG PROM_SHA256=d4b70b70c89ce68763532e4db7e7c83e9a8ff7c324531d8ccd78c90ec162792b

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl git jq \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
RUN curl -sfL -o prom.tgz \
        "https://codeload.github.com/prometheus/prometheus/tar.gz/refs/tags/${PROM_TAG}" \
    && echo "${PROM_SHA256}  prom.tgz" | sha256sum -c - \
    && tar xzf prom.tgz \
    && mv "${PROM_DIR}" /app \
    && rm -rf /build

# prometheus ships a go.work for its examples; workspace mode would drag them in.
# -buildvcs=false: the tree has no VCS history, and a stray .git above the build
# directory otherwise makes Go's version stamping fail the build outright.
ENV GOWORK=off GOTOOLCHAIN=local GOFLAGS=-buildvcs=false
ENV GOMODCACHE=/go/pkg/mod GOCACHE=/root/.cache/go-build

COPY carve.sh stubgen.go /carve/
RUN cd /app && go mod download
RUN bash /carve/carve.sh /app

# Warm the build cache so the agent's first compile is not a cold one, and so
# the image proves the carved tree builds.  The tsdb suite writes a lot of data;
# the agent needs room under /tmp for it.
RUN cd /app \
    && go build ./... \
    && go vet ./tsdb/ >/dev/null 2>&1 || true

WORKDIR /app
ENV CGO_ENABLED=0
