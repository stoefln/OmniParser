FROM runpod/pytorch:2.0.1-py3.10-cuda11.8.0-devel-ubuntu22.04

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    WORKSPACE_DIR=/app \
    MODE_TO_RUN=pod \
    OMNIPARSER_HOST=0.0.0.0 \
    OMNIPARSER_PORT=8000

ARG OMNIPARSER_MODEL_REPO=microsoft/OmniParser-v2.0

WORKDIR ${WORKSPACE_DIR}

RUN apt-get update --yes --quiet && \
    DEBIAN_FRONTEND=noninteractive apt-get install --yes --quiet --no-install-recommends \
    curl \
    ffmpeg \
    libglib2.0-0 \
    libgl1 \
    openssh-server && \
    rm -rf /var/lib/apt/lists/*

COPY requirements-runpod.txt ./requirements-runpod.txt

RUN pip install --upgrade pip && \
    pip install -r requirements-runpod.txt

COPY . .

RUN rm -rf weights/icon_detect weights/icon_caption weights/icon_caption_florence && \
    mkdir -p weights && \
    huggingface-cli download ${OMNIPARSER_MODEL_REPO} --local-dir weights --repo-type model --include "icon_detect/*" && \
    huggingface-cli download ${OMNIPARSER_MODEL_REPO} --local-dir weights --repo-type model --include "icon_caption/*" && \
    mv weights/icon_caption weights/icon_caption_florence && \
    chmod +x /app/start.sh

EXPOSE 8000

CMD ["/app/start.sh"]