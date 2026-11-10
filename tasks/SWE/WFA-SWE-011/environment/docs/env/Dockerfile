FROM python:3.9-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ git  && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
# all Python packages resolved as of the PR merge date (uv --exclude-newer)
RUN uv pip install --system --no-cache --exclude-newer 2022-01-25T00:00:00Z \
    "setuptools<60" wheel "cython==0.29.26" "numpy==1.21.5" "scipy==1.7.3" "pandas==1.3.5" patsy matplotlib pytest joblib setuptools_scm
ENV http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY=
