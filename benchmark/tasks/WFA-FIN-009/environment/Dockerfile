FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends bash git curl ca-certificates procps ripgrep && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir beautifulsoup4==4.12.3 lxml==5.3.0 html5lib==1.1
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /workspace
COPY public/ /workspace/
RUN mkdir -p /workspace/output /workspace/work /workspace/tmp
