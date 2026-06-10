import asyncio
import json
import os
from pathlib import Path

from omnitool.omniparserserver.service import OmniParserRuntime, OmniParserSettings


runtime = OmniParserRuntime(OmniParserSettings.from_env())


def _read_event_from_env() -> dict:
    event_path = os.getenv("RUNPOD_TEST_EVENT")
    if not event_path:
        raise RuntimeError("Set RUNPOD_TEST_EVENT to a JSON file for local pod-mode handler tests")

    with Path(event_path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


async def handler(event: dict) -> dict:
    input_payload = event.get("input") or {}
    image_base64 = input_payload.get("base64_image")
    if not image_base64:
        raise ValueError("input.base64_image is required")

    return runtime.parse_image(image_base64)


if __name__ == "__main__":
    mode_to_run = os.getenv("MODE_TO_RUN", "pod")
    if mode_to_run == "pod":
        print(asyncio.run(handler(_read_event_from_env())))
    else:
        import runpod

        runpod.serverless.start({"handler": handler})