FROM python:3.11
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg tesseract-ocr libgl1 libglib2.0-0 git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install --no-cache-dir \
      https://download.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl
RUN python3 -m pip install --no-cache-dir \
      "pydantic-core<2.30" "pydantic<2.11" "anthropic>=0.40.0,<0.45" \
      "google-genai>=0.3.0" "openai-whisper>=20231117" "librosa>=0.10.1" \
      "Pillow>=10.0.0" "numpy>=1.24,<2" "pyyaml>=6.0" "scenedetect>=0.6.4" \
      "ImageHash>=4.3.1" "pytesseract>=0.3.10"
RUN python3 -c "import whisper; whisper.load_model('base', device='cpu')"
RUN mkdir -p /baked
WORKDIR /workspace
RUN mkdir -p /workspace/materials /workspace/output /workspace/work
CMD ["python3"]
