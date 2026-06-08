"""
CLI replacement for OmniTool Gradio app.

Example:
python app.py --task "Open YouTube and search for cat videos" --model "omniparser + gpt-4.1-mini" --provider openai --host_control_url localhost:5000 --omniparser_server_url localhost:8000
"""

import argparse
import os
from datetime import datetime
from enum import StrEnum
from functools import partial
from pathlib import Path
from typing import cast

from anthropic import APIResponse
from anthropic.types import TextBlock
from anthropic.types.beta import BetaMessage, BetaTextBlock, BetaToolUseBlock
from anthropic.types.tool_use_block import ToolUseBlock
from requests.exceptions import RequestException
import requests

from loop import APIProvider, sampling_loop_sync
from tools import ToolResult

CONFIG_DIR = Path("~/.anthropic").expanduser()
API_KEY_FILE = CONFIG_DIR / "api_key"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"

INTRO_TEXT = (
    "OmniParser lets you turn any vision-language model into an AI agent. "
    "This CLI preserves the same backend flow as the Gradio app.\n"
    "Commands: /clear (reset history), /stop (stop after current step), /exit (quit)."
)


SUPPORTED_MODELS = [
    "omniparser + gpt-4.1-mini",
    "omniparser + gpt-4o",
    "omniparser + o1",
    "omniparser + o3-mini",
    "omniparser + R1",
    "omniparser + qwen2.5vl",
    "claude-3-5-sonnet-20241022",
    "omniparser + gpt-4o-orchestrated",
    "omniparser + o1-orchestrated",
    "omniparser + o3-mini-orchestrated",
    "omniparser + R1-orchestrated",
    "omniparser + qwen2.5vl-orchestrated",
]


class Sender(StrEnum):
    USER = "user"
    BOT = "assistant"
    TOOL = "tool"


def load_env_file(env_path: Path) -> None:
    """Load KEY=VALUE pairs from a .env file into process environment."""
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def parse_arguments():
    parser = argparse.ArgumentParser(description="OmniTool CLI App")
    parser.add_argument("--windows_host_url", type=str, default="")
    parser.add_argument("--omniparser_server_url", type=str, default="localhost:8000")
    parser.add_argument(
        "--host_control_url",
        type=str,
        default=os.getenv("OMNITOOL_HOST_CONTROL_URL", "localhost:5000"),
    )
    parser.add_argument("--task", type=str, default="")
    parser.add_argument("--model", type=str, default="omniparser + gpt-4.1-mini", choices=SUPPORTED_MODELS)
    parser.add_argument("--provider", type=str, default="")
    parser.add_argument("--api_key", type=str, default="")
    parser.add_argument("--only_n_most_recent_images", type=int, default=2)
    parser.add_argument("--max_tokens", type=int, default=16384)
    parser.add_argument("--max_steps", type=int, default=0, help="0 means unlimited")
    return parser.parse_args()


def normalize_service_url(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"
    return url


def setup_state(state):
    if "messages" not in state:
        state["messages"] = []
    if "model" not in state:
        state["model"] = "omniparser + gpt-4.1-mini"
    if "provider" not in state:
        state["provider"] = "openai"
    if "openai_api_key" not in state:
        state["openai_api_key"] = os.getenv("OPENAI_API_KEY", "")
    if "anthropic_api_key" not in state:
        state["anthropic_api_key"] = os.getenv("ANTHROPIC_API_KEY", "")
    if "api_key" not in state:
        state["api_key"] = state.get("openai_api_key", "")
    if "auth_validated" not in state:
        state["auth_validated"] = False
    if "responses" not in state:
        state["responses"] = {}
    if "tools" not in state:
        state["tools"] = {}
    if "only_n_most_recent_images" not in state:
        state["only_n_most_recent_images"] = 2
    if "chatbot_messages" not in state:
        state["chatbot_messages"] = []
    if "stop" not in state:
        state["stop"] = False


def _api_response_callback(response: APIResponse[BetaMessage], response_state: dict):
    response_id = datetime.now().isoformat()
    response_state[response_id] = response


def _tool_output_callback(tool_output: ToolResult, tool_id: str, tool_state: dict):
    tool_state[tool_id] = tool_output


def _choose_provider_for_model(model_selection: str) -> str:
    if model_selection == "claude-3-5-sonnet-20241022":
        provider_choices = [option.value for option in APIProvider if option.value != "openai"]
    elif model_selection in {
        "omniparser + gpt-4.1-mini",
        "omniparser + gpt-4o",
        "omniparser + o1",
        "omniparser + o3-mini",
        "omniparser + gpt-4o-orchestrated",
        "omniparser + o1-orchestrated",
        "omniparser + o3-mini-orchestrated",
    }:
        provider_choices = ["openai"]
    elif model_selection == "omniparser + R1":
        provider_choices = ["groq"]
    elif model_selection == "omniparser + qwen2.5vl":
        provider_choices = ["dashscope"]
    else:
        provider_choices = [option.value for option in APIProvider]
    return provider_choices[0]


def _infer_api_key(provider: str, state: dict, cli_api_key: str) -> str:
    if cli_api_key:
        state[f"{provider}_api_key"] = cli_api_key
        return cli_api_key

    if provider == "openai":
        return state.get("openai_api_key", "")
    if provider == "anthropic":
        return state.get("anthropic_api_key", "")

    env_name = f"{provider.upper()}_API_KEY"
    return os.getenv(env_name, state.get(f"{provider}_api_key", ""))


def chatbot_output_callback(message, chatbot_state, hide_images=False, sender="bot"):
    def _render_message(message_obj: str | BetaTextBlock | BetaToolUseBlock | ToolResult, hide_images=False):
        if isinstance(message_obj, str):
            return message_obj

        is_tool_result = not isinstance(message_obj, str) and (
            isinstance(message_obj, ToolResult)
            or message_obj.__class__.__name__ == "ToolResult"
        )
        if not message_obj or (
            is_tool_result
            and hide_images
            and not hasattr(message_obj, "error")
            and not hasattr(message_obj, "output")
        ):
            return None

        if is_tool_result:
            message_obj = cast(ToolResult, message_obj)
            if message_obj.output:
                return message_obj.output
            if message_obj.error:
                return f"Error: {message_obj.error}"
            if message_obj.base64_image and not hide_images:
                return "<image>"

        elif isinstance(message_obj, BetaTextBlock) or isinstance(message_obj, TextBlock):
            return f"Analysis: {message_obj.text}"
        elif isinstance(message_obj, BetaToolUseBlock) or isinstance(message_obj, ToolUseBlock):
            return f"Next I will perform the following action: {message_obj.input}"
        else:
            return str(message_obj)

    rendered = _render_message(message, hide_images)
    if rendered is None:
        return

    if sender == "bot":
        chatbot_state.append((None, rendered))
        print(f"BOT: {rendered}")
    else:
        chatbot_state.append((rendered, None))
        print(f"USER: {rendered}")


def valid_params(user_input, state, args):
    """Validate all requirements and return a list of error messages."""
    errors = []

    for server_name, url in [
        ("Windows Host", args.host_control_url),
        ("OmniParser Server", args.omniparser_server_url),
    ]:
        try:
            probe_url = f"{normalize_service_url(url)}/probe"
            response = requests.get(probe_url, timeout=3)
            if response.status_code != 200:
                errors.append(f"{server_name} is not responding at {normalize_service_url(url)}")
        except RequestException:
            errors.append(f"{server_name} is not responding at {normalize_service_url(url)}")

    if not state["api_key"].strip():
        errors.append("LLM API Key is not set")

    if not user_input:
        errors.append("no computer use request provided")

    return errors


def process_input(user_input, state, args):
    if state["stop"]:
        state["stop"] = False

    errors = valid_params(user_input, state, args)
    if errors:
        raise RuntimeError("Validation errors: " + ", ".join(errors))

    state["messages"].append(
        {
            "role": Sender.USER,
            "content": [TextBlock(type="text", text=user_input)],
        }
    )
    state["chatbot_messages"].append((user_input, None))
    print(f"USER: {user_input}")

    step_count = 0
    for loop_msg in sampling_loop_sync(
        model=state["model"],
        provider=state["provider"],
        messages=state["messages"],
        output_callback=partial(chatbot_output_callback, chatbot_state=state["chatbot_messages"], hide_images=False),
        tool_output_callback=partial(_tool_output_callback, tool_state=state["tools"]),
        api_response_callback=partial(_api_response_callback, response_state=state["responses"]),
        api_key=state["api_key"],
        only_n_most_recent_images=state["only_n_most_recent_images"],
        max_tokens=args.max_tokens,
        omniparser_url=args.omniparser_server_url,
    ):
        step_count += 1
        if loop_msg is None or state.get("stop"):
            print("End of task. Close the loop.")
            break
        if args.max_steps and step_count >= args.max_steps:
            print(f"Reached max steps ({args.max_steps}). Stopping loop.")
            break


def clear_chat(state):
    state["messages"] = []
    state["responses"] = {}
    state["tools"] = {}
    state["chatbot_messages"] = []
    print("Chat history cleared.")


def stop_app(state):
    state["stop"] = True
    print("Stop requested. Loop will stop after current step.")


def configure_state_from_args(state: dict, args) -> None:
    state["model"] = args.model

    default_provider = _choose_provider_for_model(args.model)
    state["provider"] = args.provider or default_provider

    state["api_key"] = _infer_api_key(state["provider"], state, args.api_key)
    state["only_n_most_recent_images"] = args.only_n_most_recent_images


def run_cli(args):
    os.environ["OMNITOOL_HOST_CONTROL_URL"] = normalize_service_url(args.host_control_url)

    state = {}
    setup_state(state)
    configure_state_from_args(state, args)

    print(INTRO_TEXT)
    print(
        f"Model: {state['model']} | Provider: {state['provider']} | "
        f"HostControl: {normalize_service_url(args.host_control_url)} | "
        f"OmniParser: {normalize_service_url(args.omniparser_server_url)}"
    )

    if args.task:
        process_input(args.task, state, args)
        return

    while True:
        try:
            user_input = input("\nTask> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            return

        if not user_input:
            continue
        if user_input.lower() in {"/exit", "exit", "quit"}:
            print("Exiting.")
            return
        if user_input.lower() == "/clear":
            clear_chat(state)
            continue
        if user_input.lower() == "/stop":
            stop_app(state)
            continue

        process_input(user_input, state, args)


if __name__ == "__main__":
    load_env_file(ENV_FILE)
    arguments = parse_arguments()
    run_cli(arguments)
