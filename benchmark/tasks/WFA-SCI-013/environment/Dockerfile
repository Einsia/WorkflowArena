FROM python:3.9-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends procps && rm -rf /var/lib/apt/lists/*
# OpenBLAS Cooperlake kernels give wrong/non-deterministic GEMM/SVD; force Haswell kernels.
ENV OPENBLAS_CORETYPE=Haswell PIP_DISABLE_PIP_VERSION_CHECK=1
COPY build/constraints.txt /opt/constraints.txt
RUN pip install --no-cache-dir -c /opt/constraints.txt numpy scipy pandas scikit-learn xgboost "Cython<3"
RUN pip install --no-cache-dir --no-build-isolation -c /opt/constraints.txt pymatgen==2021.3.9 matminer==0.6.5
RUN pip install --no-cache-dir -c /opt/constraints.txt spglib==2.0.2 \
    && python3 -c "import pymatgen, matminer, xgboost, sklearn; print('xgboost', xgboost.__version__, 'sklearn', sklearn.__version__)"
COPY fetch/ /opt/fetch/
COPY inputs/ /workspace/inputs/
RUN python3 -I /opt/fetch/fetch_inputs.py --manifest /opt/fetch/sources.json --destination /workspace/inputs && rm -rf /opt/fetch
WORKDIR /workspace
RUN mkdir -p /workspace/submission
