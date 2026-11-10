# Generated from the pinned upstream task recipe; environment/ and tests/
# Dockerfiles share every layer up to the start-tree build so the verifier image hits the build cache.
# Build-time network: apt/PyPI and codeload.github.com (pinned commit tarballs). Proxy via --build-arg only.
FROM python:3.9-bookworm@sha256:ff12c273af1e1814efcd8dfdefe16a70a4d901afe94dce721ffed8a34176f285 AS base
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 UV_HTTP_TIMEOUT=300 OPENBLAS_CORETYPE=Haswell
RUN pip install -q uv==0.13.5
RUN uv pip install --system --exclude-newer 2021-11-23 'numpy<1.20' 'scipy<1.8' 'cython<3' 'setuptools<60' wheel packaging pytest pytest-rerunfailures
RUN git config --global --add safe.directory '*'

# start tree = upstream first-parent commit (+ non-target paths from the PR merge), digest-checked
FROM base AS src
RUN set -eu; \
    mkdir -p /src/start /src/head; \
    curl -fsSL --retry 5 https://codeload.github.com/qutip/qutip/tar.gz/6d099443f7a96cda669580bc40d62f7b97e5cf0f | tar -xz --strip-components=1 -C /src/start; \
    curl -fsSL --retry 5 https://codeload.github.com/qutip/qutip/tar.gz/9f065865b061fd6a99e0270d77286d30812bde7a | tar -xz --strip-components=1 -C /src/head; \
    for p in qutip/nonmarkov/dlheom_solver.py qutip/tests/test_dlheom_solver.py qutip/tests/test_heom_solver.py; do rm -rf "/src/start/$p"; if [ -e "/src/head/$p" ]; then mkdir -p "$(dirname "/src/start/$p")"; cp -a "/src/head/$p" "/src/start/$p"; fi; done; \
    rm -rf /src/head; \
    cd /src/start; \
    H=$(find . -type f | LC_ALL=C sort | xargs -d '\n' sha256sum | sha256sum | cut -d' ' -f1); \
    echo "start tree $H"; \
    test "$H" = fe8f472b7c2d644b8e82c7faceeaca4c4f4fbba281d9444058d11c6e5790035b; \
    find . -type f | LC_ALL=C sort > /src/start-files.txt; \
    find . -type l | LC_ALL=C sort > /src/start-links.txt

FROM base
COPY --from=src /src/start /workspace/qutip
COPY --from=src /src/start-files.txt /src/start-links.txt /opt/wfs/
COPY wfs-build.sh /opt/wfs/build.sh
RUN mkdir -p /cache && cd /workspace/qutip && bash -c '. /opt/wfs/build.sh && (do_install) && cd /workspace/qutip && do_import'
WORKDIR /workspace
# public task material (interface/ and environment.md)
COPY interface/ /workspace/interface/
COPY environment.md /workspace/environment.md
