# Starting environment for wfa-carve-sqlglot-01.
#
# Source: tobymao/sqlglot v30.20.0, fetched from codeload and verified against
# the SHA-256 pinned below in this Dockerfile.  The tarball carries no VCS
# history, so the removed implementation cannot be recovered with a checkout,
# and no wheel of sqlglot itself is installed — the only copy of the package in
# the image is the carved tree under /app.
#
# Build needs the network.  The agent and the verifier run with no network, so
# every test dependency is pinned and installed here.
FROM python:3.12.7-slim-bookworm

ARG SQLGLOT_TAG=v30.20.0
ARG SQLGLOT_DIR=sqlglot-30.20.0
ARG SQLGLOT_SHA256=8f4f040ed164fdb9947c73423240662976b5ef6f8af8179d378fe0a26ce5c2cd

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl git jq \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
RUN curl -sfL -o sqlglot.tgz \
        "https://codeload.github.com/tobymao/sqlglot/tar.gz/refs/tags/${SQLGLOT_TAG}" \
    && echo "${SQLGLOT_SHA256}  sqlglot.tgz" | sha256sum -c - \
    && tar xzf sqlglot.tgz \
    && mv "${SQLGLOT_DIR}" /app \
    && rm -rf /build

# Pinned test dependencies, installed at build time because nothing can be
# fetched later.  pytest-subtests makes each `subTest` case a reported unit and
# pytest-reportlog writes them to a machine-readable log, which is how the
# fixture cases are scored one by one.
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade "pip==24.3.1" "setuptools==75.6.0" "wheel==0.45.1" \
    && /opt/venv/bin/pip install --no-cache-dir \
        "pytest==8.4.2" \
        "pytest-subtests==0.14.2" \
        "pytest-reportlog==0.4.0" \
        "duckdb==1.4.2" \
        "pandas==2.3.3" \
        "python-dateutil==2.9.0.post0" \
        "pytz==2025.2" \
        "typing_extensions==4.15.0" \
    && /opt/venv/bin/pip freeze > /opt/venv/pins.txt

# The test suite fans out over an unbounded ProcessPoolExecutor, which CPython
# 3.12 sizes from the host's core count rather than this container's CPU quota.
# See the file's docstring; without it the suite is OOM-killed on a big host.
COPY sitecustomize.py /opt/venv/lib/python3.12/site-packages/sitecustomize.py
ENV WFA_CPU_COUNT=4

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_INDEX=1

# setuptools_scm derives the version from VCS metadata the tarball does not
# carry; write the pinned one so `import sqlglot.__main__` works.
RUN printf "__version__ = version = '30.20.0'\n__version_tuple__ = version_tuple = (30, 20, 0)\n" \
        > /app/sqlglot/_version.py

COPY carve.sh stubgen.py /carve/
RUN bash /carve/carve.sh /app

# Prove the starting tree is usable. Deliberately not "a retained suite passes":
# the retained suite is supposed to fail here — the optimizer it calls into is
# gone, and that is the whole point of the starting tree. What must hold is that
# the suite still *collects* (no import-time explosion), that the pinned plugins
# are active, and that the untouched parser and generator still work.
WORKDIR /app
RUN python -m pytest tests/ --collect-only -q -p no:cacheprovider > /tmp/collect.txt 2>&1 \
        || { tail -30 /tmp/collect.txt; exit 1; } \
    && tail -1 /tmp/collect.txt \
    && python -c "import pytest_subtests, pytest_reportlog, duckdb, pandas; print('plugins ok')" \
    && python -c "import sqlglot, os; print('cpu_count', os.cpu_count()); \
assert sqlglot.transpile('SELECT a FROM t WHERE 1 = 1')[0] == 'SELECT a FROM t WHERE 1 = 1'; \
print('parser+generator ok')" \
    && test ! -d /app/.git
