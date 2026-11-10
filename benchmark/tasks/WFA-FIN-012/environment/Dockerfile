FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends bash git build-essential procps \
    && rm -rf /var/lib/apt/lists/*
# OpenBLAS Cooperlake kernels give wrong/non-deterministic GEMM/SVD; force Haswell kernels.
ENV OPENBLAS_CORETYPE=Haswell
RUN pip install --no-cache-dir numpy==2.1.3 scipy==1.14.1 pandas==2.2.3 openpyxl==3.1.5 xlrd==2.0.1 \
    lxml==5.3.0 beautifulsoup4==4.12.3
WORKDIR /workspace
COPY inputs/ /workspace/inputs/
# the task text says "write to output/": make that path land in the graded directory
RUN mkdir -p /workspace/submission && ln -s submission /workspace/output
