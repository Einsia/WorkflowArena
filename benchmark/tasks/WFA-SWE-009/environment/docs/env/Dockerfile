FROM python:3.8-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ git  && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
# all Python packages resolved as of the PR merge date (uv --exclude-newer)
RUN uv pip install --system --no-cache --exclude-newer 2020-06-25T00:00:00Z \
    "setuptools<50" wheel "cython==0.29.20" "numpy==1.18.5" "scipy==1.4.1" "pandas==1.0.5" patsy matplotlib pytest joblib
ENV http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY=
