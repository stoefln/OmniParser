#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PYTHON="${OMNIPARSER_VENV_PYTHON:-$ROOT_DIR/.venv311/bin/python}"
HOST="${OMNIPARSER_HOST:-127.0.0.1}"
PORT="${OMNIPARSER_PORT:-8001}"
DEVICE="${OMNIPARSER_DEVICE:-mps}"
PRELOAD="${OMNIPARSER_PRELOAD:-false}"

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "Missing Python environment at $VENV_PYTHON" >&2
  echo "Create it with: /opt/homebrew/bin/python3.11 -m venv .venv311" >&2
  echo "Then install: .venv311/bin/pip install -r requirements-runpod.txt" >&2
  exit 1
fi

if [[ ! -f "$ROOT_DIR/weights/icon_detect/model.pt" ]]; then
  echo "Missing weights at $ROOT_DIR/weights/icon_detect/model.pt" >&2
  echo "Populate ./weights first, either from the Docker image or by downloading from Hugging Face." >&2
  exit 1
fi

cd "$ROOT_DIR"

export PYTHONUNBUFFERED=1
export OMNIPARSER_DEVICE="$DEVICE"
export OMNIPARSER_HOST="$HOST"
export OMNIPARSER_PORT="$PORT"
export OMNIPARSER_PRELOAD="$PRELOAD"

exec "$VENV_PYTHON" omnitool/omniparserserver/omniparserserver.py --host "$HOST" --port "$PORT" --device "$DEVICE"