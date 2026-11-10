FROM python:3.9-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ git  && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
# all Python packages resolved as of the PR merge date (uv --exclude-newer)
RUN uv pip install --system --no-cache --exclude-newer 2021-07-28T00:00:00Z \
    "setuptools<58" wheel "cython==0.29.23" "numpy==1.20.3" "scipy==1.6.3" "pandas==1.2.5" patsy matplotlib pytest joblib setuptools_scm
ENV http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY=
ENV OPENBLAS_CORETYPE=Haswell MPLBACKEND=Agg OMP_NUM_THREADS=4
# start tree (derived_head_minus_target; digest in /workspace/MANIFEST.md), prebuilt and importable
COPY start.tar.gz prebuild.cmds /tmp/
RUN mkdir -p /work && tar -xzf /tmp/start.tar.gz -C /work && rm /tmp/start.tar.gz
RUN bash -c 'set -e; . /tmp/prebuild.cmds; bash -c "$BUILD_CMD"; bash -c "$IMPORT_CHECK"' && rm /tmp/prebuild.cmds
COPY docs/ /workspace/
WORKDIR /workspace
