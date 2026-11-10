FROM python:3.12-slim
RUN pip install --no-cache-dir --quiet "pandas==2.2.3" "openpyxl==3.1.5"
WORKDIR /workspace
COPY workspace/ /workspace/
COPY bin/ /usr/local/bin/
RUN printf '#!/bin/sh\nexec python3 /usr/local/bin/ooo_sys.py "$@"\n' > /usr/local/bin/sys && \
    chmod +x /usr/local/bin/sys && mkdir -p /workspace/submission
ENV OOO_DB=/workspace/state.db
