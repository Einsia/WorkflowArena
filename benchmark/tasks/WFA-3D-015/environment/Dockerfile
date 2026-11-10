FROM workflowarena-original-cdc-tools:20261022
USER root
# v0.2 (2026-10-25): the statement promises espeak-ng and sox for offline dialogue/foley; the base image lacks them
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends espeak-ng sox \
    && rm -rf /var/lib/apt/lists/*
COPY input /workspace/input
COPY CREDITS.md /workspace/CREDITS.md
RUN mkdir -p /workspace/output /workspace/work
WORKDIR /workspace
