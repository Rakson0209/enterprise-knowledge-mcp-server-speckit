# Enterprise Knowledge MCP Server — built for the deployment node:
# Zeabur Arm Ampere A1 Compute (linux/arm64, no GPU). All inference is CPU-only.
FROM --platform=linux/arm64 python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    KB_DATA_DIR=/data \
    HF_HOME=/data/models/hf \
    TORCH_HOME=/data/models/torch

WORKDIR /app

# System libraries required by docling / onnxruntime (RapidOCR) / pdf handling.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libgl1 \
        libglib2.0-0 \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY app ./app

# Install CPU-only torch FIRST. On linux/arm64 the *default* torch wheel now drags in multi-GB
# CUDA libraries (nvidia-*-cu13, cuda-toolkit) that are useless on the GPU-less Ampere node and
# bloat the image until the build export fails. The PyTorch CPU index serves a lean aarch64 CPU
# wheel; once torch is satisfied, installing the project reuses it (no CUDA pulled transitively).
RUN pip install --upgrade pip \
 && pip install --index-url https://download.pytorch.org/whl/cpu torch \
 && pip install .

# Persistent volume: Chroma index, uploads, and model cache survive restart/redeploy.
VOLUME ["/data"]

EXPOSE 8000

# Liveness: GET /health
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
