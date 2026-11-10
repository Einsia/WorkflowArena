FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends bash git build-essential procps \
    && rm -rf /var/lib/apt/lists/*
# OpenBLAS Cooperlake kernels give wrong/non-deterministic GEMM/SVD; force Haswell kernels.
ENV OPENBLAS_CORETYPE=Haswell
RUN pip install --no-cache-dir numpy==2.1.3 scipy==1.14.1 pandas==2.2.3 openpyxl==3.1.5 xlrd==2.0.1 \
    statsmodels==0.14.4 matplotlib==3.9.2 h5py==3.12.1
WORKDIR /workspace
COPY inputs/ /workspace/inputs/
RUN mkdir -p /workspace/submission
