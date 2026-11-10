FROM workflowarena-original-cdc-tools:20261022
USER root
COPY input /workspace/input
COPY fetch/ /opt/workflowarena-source/
RUN python3 /opt/workflowarena-source/fetch_inputs.py --manifest /opt/workflowarena-source/sources.json --destination /workspace/input && rm -rf /opt/workflowarena-source
COPY CREDITS.md /workspace/CREDITS.md
RUN mkdir -p /workspace/output /workspace/work
WORKDIR /workspace
