import argparse
import base64
import binascii
import io
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOM_MODEL_PATH = REPO_ROOT / "weights" / "icon_detect" / "model.pt"
DEFAULT_CAPTION_MODEL_PATH = REPO_ROOT / "weights" / "icon_caption_florence"


def _get_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class OmniParserSettings:
    som_model_path: str
    caption_model_name: str
    caption_model_path: str
    device: str
    box_threshold: float
    host: str
    port: int
    preload: bool

    @classmethod
    def from_env(cls) -> "OmniParserSettings":
        return cls(
            som_model_path=os.getenv("OMNIPARSER_SOM_MODEL_PATH", str(DEFAULT_SOM_MODEL_PATH)),
            caption_model_name=os.getenv("OMNIPARSER_CAPTION_MODEL_NAME", "florence2"),
            caption_model_path=os.getenv("OMNIPARSER_CAPTION_MODEL_PATH", str(DEFAULT_CAPTION_MODEL_PATH)),
            device=os.getenv("OMNIPARSER_DEVICE", "cpu"),
            box_threshold=float(os.getenv("OMNIPARSER_BOX_THRESHOLD", "0.05")),
            host=os.getenv("OMNIPARSER_HOST", "127.0.0.1"),
            port=int(os.getenv("OMNIPARSER_PORT", "8000")),
            preload=_get_bool_env("OMNIPARSER_PRELOAD", True),
        )

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "OmniParserSettings":
        env_settings = cls.from_env()
        return cls(
            som_model_path=args.som_model_path or env_settings.som_model_path,
            caption_model_name=args.caption_model_name or env_settings.caption_model_name,
            caption_model_path=args.caption_model_path or env_settings.caption_model_path,
            device=args.device or env_settings.device,
            box_threshold=args.box_threshold if args.box_threshold is not None else env_settings.box_threshold,
            host=args.host or env_settings.host,
            port=args.port or env_settings.port,
            preload=env_settings.preload,
        )

    def to_model_config(self) -> dict:
        return {
            "som_model_path": self.som_model_path,
            "caption_model_name": self.caption_model_name,
            "caption_model_path": self.caption_model_path,
            "device": self.device,
            "BOX_TRESHOLD": self.box_threshold,
        }


class ParseRequest(BaseModel):
    base64_image: str
    include_image: bool = False


class OmniParserRuntime:
    def __init__(self, settings: OmniParserSettings):
        self.settings = settings
        self._parser = None
        self._init_error = None
        self._initialized_at = None
        self._lock = threading.Lock()

    def ensure_initialized(self):
        if self._parser is not None:
            return self._parser

        with self._lock:
            if self._parser is not None:
                return self._parser

            try:
                from util.omniparser import Omniparser

                self._parser = Omniparser(self.settings.to_model_config())
                self._initialized_at = time.time()
                self._init_error = None
            except Exception as exc:
                self._init_error = str(exc)
                raise RuntimeError(f"Failed to initialize OmniParser: {exc}") from exc

        return self._parser

    def status(self) -> dict:
        return {
            "ready": self._parser is not None,
            "initialized_at": self._initialized_at,
            "error": self._init_error,
            "device": self.settings.device,
            "som_model_path": self.settings.som_model_path,
            "caption_model_path": self.settings.caption_model_path,
        }

    def parse_image(self, image_base64: str, include_image: bool = False) -> dict[str, Any]:
        total_start = time.time()

        validate_start = time.time()
        self._validate_image(image_base64)
        validate_duration = time.time() - validate_start

        init_start = time.time()
        parser = self.ensure_initialized()
        init_duration = time.time() - init_start

        parse_start = time.time()
        parse_result = parser.parse(image_base64, include_image=include_image)
        parse_duration = time.time() - parse_start

        response = {
            "parsed_content_list": parse_result["parsed_content_list"],
            "latency": parse_duration,
            "timings": {
                "validate_s": validate_duration,
                "init_s": init_duration,
                "parse_s": parse_duration,
                "total_s": time.time() - total_start,
                **parse_result["timings"],
            },
        }
        if parse_result["som_image_base64"] is not None:
            response["som_image_base64"] = parse_result["som_image_base64"]
        return response

    @staticmethod
    def _validate_image(image_base64: str) -> None:
        try:
            image_bytes = base64.b64decode(image_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("base64_image must be valid base64 data") from exc

        try:
            with Image.open(io.BytesIO(image_bytes)) as image:
                image.verify()
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise ValueError("base64_image must decode to a valid image") from exc


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OmniParser API")
    parser.add_argument("--som_model_path", type=str, help="Path to the som model")
    parser.add_argument("--caption_model_name", type=str, help="Name of the caption model")
    parser.add_argument("--caption_model_path", type=str, help="Path to the caption model")
    parser.add_argument("--device", type=str, help="Device to run the model")
    parser.add_argument(
        "--BOX_TRESHOLD",
        "--box-threshold",
        dest="box_threshold",
        type=float,
        help="Threshold for box detection",
    )
    parser.add_argument("--host", type=str, help="Host for the API")
    parser.add_argument("--port", type=int, help="Port for the API")
    return parser


def create_app(runtime: OmniParserRuntime) -> FastAPI:
    app = FastAPI(title="OmniParser API")

    @app.on_event("startup")
    async def preload_model() -> None:
        if runtime.settings.preload:
            runtime.ensure_initialized()

    @app.post("/parse/")
    async def parse(parse_request: ParseRequest):
        try:
            return runtime.parse_image(parse_request.base64_image, include_image=parse_request.include_image)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/probe/")
    async def probe():
        status = runtime.status()
        status_code = 200 if status["ready"] else 503
        return JSONResponse(content=status, status_code=status_code)

    return app