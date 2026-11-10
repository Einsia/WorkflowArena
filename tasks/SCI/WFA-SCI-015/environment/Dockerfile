FROM rocker/r-ver:4.0.3
# OpenBLAS Cooperlake kernels give wrong/non-deterministic GEMM/SVD; force Haswell kernels.
ENV OPENBLAS_CORETYPE=Haswell
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip python3-dev procps git \
    && rm -rf /var/lib/apt/lists/*
RUN Rscript -e 'install.packages(c("EpiEstim","deSolve","jsonlite"))' \
    && Rscript -e 'v <- as.character(packageVersion("EpiEstim")); cat("EpiEstim", v, "\n"); if (v != "2.2.4") quit(status=1); library(deSolve)'
RUN pip3 install --no-cache-dir numpy==1.24.4 scipy==1.10.1 pandas==2.0.3
WORKDIR /workspace
COPY inputs/ /workspace/inputs/
RUN mkdir -p /workspace/submission
