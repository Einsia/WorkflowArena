FROM python:3.9-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ git faketime && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
# all Python packages resolved as of the PR merge date (uv --exclude-newer)
RUN uv pip install --system --no-cache --exclude-newer 2021-04-15T00:00:00Z \
    "setuptools<55" wheel setuptools_scm "cython==0.29.22" "jinja2<3" "markupsafe<2" "extension-helpers<1" "numpy==1.20.2" pyerfa PyYAML scipy matplotlib pytest pytest-astropy hypothesis
ENV http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY=
ENV OPENBLAS_CORETYPE=Haswell MPLBACKEND=Agg OMP_NUM_THREADS=4
COPY . /tests/
WORKDIR /tests
