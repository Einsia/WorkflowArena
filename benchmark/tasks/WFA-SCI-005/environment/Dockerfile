# --- WorkflowArena science/competition shared base layers (keep identical across tasks for build cache) ---
FROM python:3.12-slim-bookworm@sha256:6a0e06f5ba0b373d051aabd3fffb9b873f27f9a2a3a14bcbe37dee6f0e3bbc70
RUN apt-get update && apt-get install -y --no-install-recommends bash git build-essential cmake procps wget ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir numpy==2.1.3 scipy==1.14.1 pandas==2.2.3 scikit-learn==1.5.2 rdkit==2024.9.6 \
    lightgbm==4.5.0 networkx==3.4.2 biopython==1.84 statsmodels==0.14.4 matplotlib==3.9.2 openpyxl==3.1.5 \
    joblib==1.4.2 tqdm==4.67.1 pyarrow==18.1.0
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.5.1+cpu
# --- end shared base ---
WORKDIR /workspace
COPY inputs/ /workspace/inputs/
COPY restore_inputs.py inputs.compression.json /opt/workflowarena/
RUN python3 /opt/workflowarena/restore_inputs.py --input-dir /workspace/inputs --manifest /opt/workflowarena/inputs.compression.json --remove-archives
COPY inputs.MANIFEST.tsv /workspace/inputs.MANIFEST.tsv
RUN mkdir -p /workspace/submission
