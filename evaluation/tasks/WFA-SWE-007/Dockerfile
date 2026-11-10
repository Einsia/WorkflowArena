FROM python:3.11-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ git gfortran libopenblas-dev liblapack-dev pkg-config && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
# all Python packages resolved as of the PR merge date (uv --exclude-newer)
RUN uv pip install --system --no-cache --exclude-newer 2023-07-10T00:00:00Z \
    "meson-python==0.13.1" "meson==1.1.1" ninja "cython==0.29.36" "pybind11==2.10.4" pythran "numpy==1.25.0" wheel setuptools pytest pytest-xdist hypothesis mpmath pooch matplotlib
ENV http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY=
ENV OPENBLAS_CORETYPE=Haswell MPLBACKEND=Agg OMP_NUM_THREADS=4
COPY . /tests/
WORKDIR /tests
