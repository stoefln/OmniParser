from pathlib import Path
from uuid import uuid4
import os
import requests
from PIL import Image
from .base import BaseAnthropicTool, ToolError
from io import BytesIO

OUTPUT_DIR = "./tmp/outputs"


def get_host_control_base_url() -> str:
    url = os.getenv("OMNITOOL_HOST_CONTROL_URL", "http://localhost:5000").strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"
    return url

def get_screenshot(resize: bool = False, target_width: int = 1920, target_height: int = 1080):
    """Capture screenshot by requesting from HTTP endpoint - returns native resolution unless resized"""
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"screenshot_{uuid4().hex}.png"
    
    try:
        response = requests.get(f"{get_host_control_base_url()}/screenshot")
        if response.status_code != 200:
            raise ToolError(f"Failed to capture screenshot: HTTP {response.status_code}")
        
        # (1280, 800)
        screenshot = Image.open(BytesIO(response.content))
        
        if resize and screenshot.size != (target_width, target_height):
            screenshot = screenshot.resize((target_width, target_height))
        screenshot.save(path)
        return screenshot, path
    except Exception as e:
        raise ToolError(f"Failed to capture screenshot: {str(e)}")