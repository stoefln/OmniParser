import argparse
import logging
import os
import shlex
import subprocess
import threading
import traceback
from io import BytesIO

import pyautogui
from flask import Flask, jsonify, request, send_file
from PIL import Image


def execute_anything(data):
    """Execute any command received in the JSON request."""
    shell = data.get("shell", False)
    command = data.get("command", "" if shell else [])

    if isinstance(command, str) and not shell:
        command = shlex.split(command)

    for i, arg in enumerate(command):
        if arg.startswith("~/"):
            command[i] = os.path.expanduser(arg)

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=shell,
            text=True,
            timeout=120,
        )
        return jsonify(
            {
                "status": "success",
                "output": result.stdout,
                "error": result.stderr,
                "returncode": result.returncode,
            }
        )
    except Exception as exc:
        logger.error("\n" + traceback.format_exc() + "\n")
        return jsonify({"status": "error", "message": str(exc)}), 500


def execute(data):
    """Default safe stub for command execution."""
    return (
        jsonify(
            {
                "status": "error",
                "message": (
                    "Command execution is disabled. Start with "
                    "--allow_unsafe_execute to enable desktop control."
                ),
            }
        ),
        500,
    )


execute_impl = execute


parser = argparse.ArgumentParser()
parser.add_argument(
    "--log_file",
    help="log file path",
    type=str,
    default=os.path.join(os.path.dirname(__file__), "server.log"),
)
parser.add_argument("--port", help="port", type=int, default=5000)
parser.add_argument("--host", help="bind host", type=str, default="127.0.0.1")
parser.add_argument(
    "--allow_unsafe_execute",
    help="allow arbitrary command execution for host control",
    action="store_true",
)
args = parser.parse_args()

if args.allow_unsafe_execute:
    execute_impl = execute_anything

logging.basicConfig(filename=args.log_file, level=logging.DEBUG, filemode="w")
logger = logging.getLogger("werkzeug")

app = Flask(__name__)
computer_control_lock = threading.Lock()


@app.route("/probe", methods=["GET"])
def probe_endpoint():
    return jsonify({"status": "Probe successful", "message": "Service is operational"}), 200


@app.route("/execute", methods=["POST"])
def execute_command():
    with computer_control_lock:
        data = request.json
        return execute_impl(data)


@app.route("/screenshot", methods=["GET"])
def capture_screen_with_cursor():
    cursor_path = os.path.join(os.path.dirname(__file__), "cursor.png")
    screenshot = pyautogui.screenshot()
    cursor_x, cursor_y = pyautogui.position()

    cursor = Image.open(cursor_path)
    cursor = cursor.resize((int(cursor.width / 1.5), int(cursor.height / 1.5)))
    screenshot.paste(cursor, (cursor_x, cursor_y), cursor)

    img_io = BytesIO()
    screenshot.save(img_io, "PNG")
    img_io.seek(0)
    return send_file(img_io, mimetype="image/png")


if __name__ == "__main__":
    app.run(host=args.host, port=args.port)
