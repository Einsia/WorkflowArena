# Generated from the pinned upstream task recipe; environment/ and tests/
# Dockerfiles share every layer up to the start-tree build so the verifier image hits the build cache.
# Build-time network: apt/PyPI and codeload.github.com (pinned commit tarballs). Proxy via --build-arg only.
FROM python:3.12-bookworm@sha256:14a4933e6cef421424f7a66d89a3f4eafcbd0d90e0a822251f298e05132dc735 AS base
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 UV_HTTP_TIMEOUT=300 OPENBLAS_CORETYPE=Haswell
RUN apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends cmake libopenblas-dev && rm -rf /var/lib/apt/lists/*
RUN pip install -q uv==0.13.5
RUN uv pip install --system --exclude-newer 2026-07-14 numpy scipy h5py pytest pytest-xdist pytest-timeout
RUN git config --global --add safe.directory '*'

# start tree = upstream first-parent commit (+ non-target paths from the PR merge), digest-checked
FROM base AS src
RUN set -eu; \
    mkdir -p /src/start /src/head; \
    curl -fsSL --retry 5 https://codeload.github.com/pyscf/pyscf/tar.gz/d3305ac1caca551dafb12d1a95a53ff7497e97ee | tar -xz --strip-components=1 -C /src/start; \
    rm -rf /src/head; \
    cd /src/start; \
    H=$(find . -type f | LC_ALL=C sort | xargs -d '\n' sha256sum | sha256sum | cut -d' ' -f1); \
    echo "start tree $H"; \
    test "$H" = 332e10d828886c8fa0c7c99fc76ed04041d55f090954447e242e632d3830f6cc; \
    find . -type f | LC_ALL=C sort > /src/start-files.txt; \
    find . -type l | LC_ALL=C sort > /src/start-links.txt

FROM base
ENV PYTHONPATH=/workspace/pyscf
COPY --from=src /src/start /workspace/pyscf
COPY --from=src /src/start-files.txt /src/start-links.txt /opt/wfs/
COPY wfs-build.sh /opt/wfs/build.sh
RUN mkdir -p /cache && cd /workspace/pyscf && bash -c '. /opt/wfs/build.sh && (do_install) && cd /workspace/pyscf && do_import'
WORKDIR /workspace
# public task material (interface/ and environment.md)
COPY interface/ /workspace/interface/
COPY environment.md /workspace/environment.md
