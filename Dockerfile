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

# Install CPU-only torch AND torchvision together from the PyTorch CPU index FIRST. Two reasons:
#  1. The default linux/arm64 torch wheel drags in the multi-GB CUDA stack (nvidia-*-cu13,
#     cuda-toolkit), useless on the GPU-less Ampere node and big enough to break the image export.
#  2. torchvision is a transitive dependency (docling); if it comes from PyPI at a version built
#     against a different torch, it fails at runtime with "operator torchvision::nms does not
#     exist", which cascades into transformers/sentence-transformers import failures. Installing
#     both from the same CPU index guarantees a matched, CPU-only pair; `pip install .` then reuses
#     them without pulling CUDA or a mismatched torchvision.
RUN pip install --upgrade pip \
 && pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision \
 && pip install .

# Persistent volume: Chroma index, uploads, and model cache survive restart/redeploy.
VOLUME ["/data"]

# Zeabur routes the public domain to 8080 and injects $PORT; bind to it (fallback 8080).
EXPOSE 8080

# Liveness: GET /health
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
