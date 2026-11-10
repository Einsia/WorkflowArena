FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends bash git build-essential procps \
    && rm -rf /var/lib/apt/lists/*
# OpenBLAS Cooperlake kernels give wrong/non-deterministic GEMM/SVD; force Haswell kernels.
ENV OPENBLAS_CORETYPE=Haswell
RUN pip install --no-cache-dir numpy==2.1.3 scipy==1.14.1 pandas==2.2.3 openpyxl==3.1.5 xlrd==2.0.1 \
    statsmodels==0.14.4 matplotlib==3.9.2 h5py==3.12.1
RUN pip install --no-cache-dir numpy==1.26.4 scipy==1.13.1 pyscf==2.8.0 pyscf-dispersion==1.3.0 \
    && python3 -c "from pyscf import gto, dft; from pyscf.dispersion import dftd3; m=gto.M(atom='H 0 0 0; H 0 0 0.74', basis='def2-svp', verbose=0); mf=dft.RKS(m); mf.xc='pbe0'; e=mf.kernel(); d=dftd3.DFTD3Dispersion(m, xc='PBE0', version='d3bj').get_dispersion()['energy']; print('pyscf smoke', e, d)"
WORKDIR /workspace
COPY inputs/ /workspace/inputs/
RUN mkdir -p /workspace/submission
