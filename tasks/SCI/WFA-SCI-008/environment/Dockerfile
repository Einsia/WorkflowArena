FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends bash git build-essential procps \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir numpy scipy pandas scikit-learn rdkit
WORKDIR /workspace
COPY inputs/ /workspace/inputs/
RUN mkdir -p /workspace/submission
