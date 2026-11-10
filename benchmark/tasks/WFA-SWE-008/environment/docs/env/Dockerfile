FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ git gfortran libopenblas-dev liblapack-dev pkg-config && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
# all Python packages resolved as of the PR merge date (uv --exclude-newer)
RUN uv pip install --system --no-cache --exclude-newer 2024-10-04T00:00:00Z \
    "meson-python>=0.16" meson ninja "cython>=3.0.8,<3.1" "pybind11>=2.13.1" pythran "numpy==2.1.1" wheel setuptools pytest pytest-xdist hypothesis mpmath pooch matplotlib
ENV http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY=
