FROM python:3.8-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ git faketime && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
# all Python packages resolved as of the PR merge date (uv --exclude-newer)
RUN uv pip install --system --no-cache --exclude-newer 2020-05-03T00:00:00Z \
    "setuptools<47" wheel setuptools_scm "cython==0.29.17" "jinja2<3" "markupsafe<2" "extension-helpers<1" "numpy==1.18.3" PyYAML scipy matplotlib pytest pytest-astropy hypothesis "asdf==2.6.0"
ENV http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY=
ENV OPENBLAS_CORETYPE=Haswell MPLBACKEND=Agg OMP_NUM_THREADS=4
COPY . /tests/
WORKDIR /tests
