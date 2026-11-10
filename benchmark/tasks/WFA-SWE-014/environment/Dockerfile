# Starting environment for wfa-carve-pydantic-01.
#
# Source: pydantic/pydantic v2.13.5, fetched from codeload and verified against
# the SHA-256 pinned below in this Dockerfile.  The tarball carries no VCS
# history, so the removed implementation cannot be recovered with a checkout.
#
# pydantic-core is the compiled Rust half of pydantic and is NOT carved.  It is
# pinned by the upstream pyproject.toml to ==2.46.5 and installed here from its
# PyPI wheel, so no Rust toolchain is needed and nothing is compiled at agent
# time.  The vendored `pydantic-core/` source directory in the tarball is the
# upstream workspace checkout; it is not built and not importable -- the wheel
# in site-packages is what `import pydantic_core` resolves to.
#
# Test dependencies are pinned to the versions pydantic v2.13.5's own uv.lock
# resolves, so the acceptance numbers are the ones upstream CI would see.
# pytest 9 cannot even collect this suite: tests/test_docs.py trips
# PytestRemovedIn10Warning and the project sets `filterwarnings = error`.
#
# Build needs the network.  The agent and the verifier run with no network.
FROM python:3.12.7-bookworm

ARG PYDANTIC_TAG=v2.13.5
ARG PYDANTIC_DIR=pydantic-2.13.5
ARG PYDANTIC_SHA256=1fbdaa516c0101553c3dfda0a85f4db040ccf9f2e75199f0c2d485ccdd55086b

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl git jq \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
RUN curl -sfL -o pydantic.tgz \
        "https://codeload.github.com/pydantic/pydantic/tar.gz/refs/tags/${PYDANTIC_TAG}" \
    && echo "${PYDANTIC_SHA256}  pydantic.tgz" | sha256sum -c - \
    && tar xzf pydantic.tgz \
    && mv "${PYDANTIC_DIR}" /app \
    && rm -rf /build

# Exact pins, resolved from the upstream uv.lock.  `pydantic` itself is NOT
# installed: /app is put on the path instead (see PYTHONPATH below), so the
# carved tree is the only pydantic in the image and site-packages cannot hold a
# pristine copy of what was removed.
RUN pip install --no-cache-dir \
        'pydantic-core==2.46.5' \
        'typing-extensions==4.14.1' \
        'annotated-types==0.7.0' \
        'typing-inspection==0.4.2' \
        'pytest==8.3.5' \
        'pytest-mock==3.14.0' \
        'pytest-benchmark==5.1.0' \
        'pytest-examples==0.0.15' \
        'pytest-run-parallel==0.7.1' \
        'pytest-pretty==1.2.0' \
        'dirty-equals==0.9.0' \
        'eval-type-backport==0.2.2' \
        'faker==35.0.0' \
        'jsonschema==4.24.0' \
        'pytz==2024.2' \
        'packaging==26.3' \
        'cloudpickle==3.1.2'

# No pydantic in site-packages, and no wheel of it left in a cache.
RUN ! python -c 'import pydantic' 2>/dev/null \
    && test ! -e /usr/local/lib/python3.12/site-packages/pydantic

# Set before the carve so that nothing in the build can drop a .pyc of an
# original module into the tree.
ENV PYTHONDONTWRITEBYTECODE=1

COPY carve.sh stubgen.py /carve/
RUN bash /carve/carve.sh /app

# Several tests spawn a subprocess that imports pydantic
# (tests/test_dataclasses.py::test_dataclass_import); the subprocess inherits
# PYTHONPATH, so this is what makes /app importable everywhere.
ENV PYTHONPATH=/app

# Prove the carved tree is collectable: the retained tests must still be
# discoverable even though every model definition in them fails.
RUN cd /app && python -m pytest tests/test_version.py -q --no-header 2>&1 | tail -3

# Timestamp reference for the verifier's "what did the agent touch" evidence.
# Outside /app so the agent cannot remove it.
RUN touch /opt/task-start-marker

WORKDIR /app
