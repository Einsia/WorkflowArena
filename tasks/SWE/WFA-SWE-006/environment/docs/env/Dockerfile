FROM python:3.9-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ git gfortran libopenblas-dev liblapack-dev pkg-config && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
# all Python packages resolved as of the PR merge date (uv --exclude-newer)
RUN uv pip install --system --no-cache --exclude-newer 2021-02-01T00:00:00Z \
    "setuptools<52" wheel "cython==0.29.21" "numpy==1.19.5" "pybind11==2.6.2" pythran pytest pytest-xdist hypothesis mpmath
ENV http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY=
