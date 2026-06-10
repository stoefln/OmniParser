#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
API_BASE_URL="${RUNPOD_API_BASE_URL:-https://api.runpod.ai/v2}"
LOCAL_ENV_FILE="$ROOT_DIR/.runpod-api-key"

if [[ -f "$LOCAL_ENV_FILE" ]]; then
    # Allow a machine-local API key file without committing secrets to git.
    # shellcheck disable=SC1090
    source "$LOCAL_ENV_FILE"
fi

API_KEY="${RUNPOD_API_KEY:-}"

if [[ $# -lt 2 || $# -gt 3 ]]; then
  echo "Usage: $0 <endpoint-id> <image-path> [output-dir]" >&2
    echo "Set RUNPOD_API_KEY or create $LOCAL_ENV_FILE before running." >&2
  exit 1
fi

if [[ -z "$API_KEY" ]]; then
  echo "RUNPOD_API_KEY is required" >&2
  exit 1
fi

ENDPOINT_ID="$1"
IMAGE_PATH="$2"
OUTPUT_DIR="${3:-$ROOT_DIR/runpod-debug}"

if [[ ! -f "$IMAGE_PATH" ]]; then
  echo "Image not found: $IMAGE_PATH" >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

IMAGE_NAME="$(basename "$IMAGE_PATH")"
IMAGE_STEM="${IMAGE_NAME%.*}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
PREFIX="$OUTPUT_DIR/${IMAGE_STEM}-${TIMESTAMP}"
PAYLOAD_FILE="$PREFIX-request.json"
RESPONSE_FILE="$PREFIX-response.json"
PARSED_FILE="$PREFIX-parsed-content.json"
DEBUG_IMAGE_FILE="$PREFIX-debug.png"
RAW_RESPONSE_FILE="$PREFIX-response.raw.json"

python3 - <<'PY' "$IMAGE_PATH" "$PAYLOAD_FILE"
import base64
import json
import pathlib
import sys

image_path = pathlib.Path(sys.argv[1])
payload_path = pathlib.Path(sys.argv[2])

payload = {
    "input": {
        "base64_image": base64.b64encode(image_path.read_bytes()).decode("ascii"),
        "include_image": True,
    }
}

payload_path.write_text(json.dumps(payload), encoding="utf-8")
PY

http_code="$({
    curl --silent --show-error -o "$RAW_RESPONSE_FILE" -w '%{http_code}' \
    "$API_BASE_URL/$ENDPOINT_ID/runsync" \
    -H 'Content-Type: application/json' \
    -H "Authorization: Bearer $API_KEY" \
    --data-binary @"$PAYLOAD_FILE"
} )"

python3 - <<'PY' "$http_code" "$RAW_RESPONSE_FILE" "$RESPONSE_FILE" "$PARSED_FILE" "$DEBUG_IMAGE_FILE"
import base64
import json
import pathlib
import sys

http_code = int(sys.argv[1])
raw_response_path = pathlib.Path(sys.argv[2])
response_path = pathlib.Path(sys.argv[3])
parsed_path = pathlib.Path(sys.argv[4])
debug_image_path = pathlib.Path(sys.argv[5])

body = raw_response_path.read_text(encoding="utf-8")

try:
    payload = json.loads(body)
except json.JSONDecodeError as exc:
    raise SystemExit(f"Runpod returned non-JSON response (HTTP {http_code}): {exc}")

if http_code != 200:
    raise SystemExit(f"Runpod request failed with HTTP {http_code}: {json.dumps(payload, indent=2)}")

output = payload.get("output")
if not isinstance(output, dict):
    raise SystemExit(f"Runpod response missing output object: {json.dumps(payload, indent=2)}")

parsed_content = output.get("parsed_content_list")
if parsed_content is not None:
    parsed_path.write_text(json.dumps(parsed_content, indent=2), encoding="utf-8")

som_image_base64 = output.get("som_image_base64")
if som_image_base64:
    debug_image_path.write_bytes(base64.b64decode(som_image_base64))
    output = dict(output)
    output.pop("som_image_base64", None)
    payload = dict(payload)
    payload["output"] = output

response_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
raw_response_path.unlink(missing_ok=True)

summary = {
    "response_file": str(response_path),
    "parsed_content_file": str(parsed_path) if parsed_content is not None else None,
    "debug_image_file": str(debug_image_path) if som_image_base64 else None,
    "latency": output.get("latency"),
    "timings": output.get("timings"),
    "executionTime": payload.get("executionTime"),
    "delayTime": payload.get("delayTime"),
    "parsed_items": len(parsed_content) if isinstance(parsed_content, list) else None,
}

print(json.dumps(summary, indent=2))
PY