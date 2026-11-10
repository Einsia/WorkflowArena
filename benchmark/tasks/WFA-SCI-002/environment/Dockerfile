# --- WorkflowArena science/competition shared base layers (keep identical across tasks for build cache) ---
FROM python:3.12-slim-bookworm@sha256:6a0e06f5ba0b373d051aabd3fffb9b873f27f9a2a3a14bcbe37dee6f0e3bbc70
RUN apt-get update && apt-get install -y --no-install-recommends bash git build-essential cmake procps wget ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir numpy==2.1.3 scipy==1.14.1 pandas==2.2.3 scikit-learn==1.5.2 rdkit==2024.9.6 \
    lightgbm==4.5.0 networkx==3.4.2 biopython==1.84 statsmodels==0.14.4 matplotlib==3.9.2 openpyxl==3.1.5 \
    joblib==1.4.2 tqdm==4.67.1 pyarrow==18.1.0
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.5.1+cpu
# --- end shared base ---
# --- structural biology tools (shared by CASP/CAPRI tasks) ---
RUN apt-get update && apt-get install -y --no-install-recommends openbabel autodock-vina \
    && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/pylelab/USalign.git /opt/USalign && cd /opt/USalign \
    && git checkout 23f14ffcf8647f2dc1c0e01043db3a7f3a661c28 && make -j8 > /tmp/usalign_build.log 2>&1 \
    && for b in USalign TMalign MMalign TMscore qTMclust; do [ -x $b ] && cp $b /usr/local/bin/; done; ls /usr/local/bin
RUN pip install --no-cache-dir ViennaRNA==2.7.2 openmm==8.2.0
WORKDIR /workspace
COPY inputs/ /workspace/inputs/
COPY fetch/ /opt/workflowarena-source/
RUN python3 /opt/workflowarena-source/fetch_inputs.py --manifest /opt/workflowarena-source/sources.json --destination /workspace/inputs && rm -rf /opt/workflowarena-source
RUN mkdir -p /workspace/submission
