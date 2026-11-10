FROM workflowarena-cdc-avb-repurpose:20261005
USER root
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends blender libegl1 libgl1 libreoffice-impress poppler-utils nodejs npm fonts-liberation && rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install --no-cache-dir pypdf python-pptx
ENV HOME=/tmp LIBGL_ALWAYS_SOFTWARE=1
WORKDIR /workspace
