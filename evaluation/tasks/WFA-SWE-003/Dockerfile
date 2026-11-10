# Generated from the pinned upstream task recipe; environment/ and tests/
# Dockerfiles share every layer up to the start-tree build so the verifier image hits the build cache.
# Build-time network: apt/PyPI and codeload.github.com (pinned commit tarballs). Proxy via --build-arg only.
FROM python:3.11-bookworm@sha256:18d373e126e39c29c6d38e71e2f19ca66636568318fc95c7849c462b7f9d3d64 AS base
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 UV_HTTP_TIMEOUT=300 OPENBLAS_CORETYPE=Haswell
RUN pip install -q uv==0.13.5
RUN uv pip install --system --exclude-newer 2025-03-28 'numpy<2.2' scipy networkx rustworkx autograd tomlkit appdirs 'autoray>=0.6.11' cachetools requests typing_extensions packaging diastatic-malt pytest pytest-mock flaky matplotlib pytest-benchmark pytest-xdist
RUN git config --global --add safe.directory '*'

# start tree = upstream first-parent commit (+ non-target paths from the PR merge), digest-checked
FROM base AS src
RUN set -eu; \
    mkdir -p /src/start /src/head; \
    curl -fsSL --retry 5 https://codeload.github.com/PennyLaneAI/pennylane/tar.gz/7e94b1379bf7a73a0b24de672399a905477b3a37 | tar -xz --strip-components=1 -C /src/start; \
    rm -rf /src/head; \
    cd /src/start; \
    H=$(find . -type f | LC_ALL=C sort | xargs -d '\n' sha256sum | sha256sum | cut -d' ' -f1); \
    echo "start tree $H"; \
    test "$H" = fe97241891e6cd9b7f85151e05d3ce6c7ac34189d0ade6d52b123ce015b0506b; \
    find . -type f | LC_ALL=C sort > /src/start-files.txt; \
    find . -type l | LC_ALL=C sort > /src/start-links.txt

FROM base
COPY --from=src /src/start /workspace/pennylane
COPY --from=src /src/start-files.txt /src/start-links.txt /opt/wfs/
COPY wfs-build.sh /opt/wfs/build.sh
RUN mkdir -p /cache && cd /workspace/pennylane && bash -c '. /opt/wfs/build.sh && (do_install) && cd /workspace/pennylane && do_import'
WORKDIR /workspace
COPY . /tests/
