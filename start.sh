#!/bin/bash
set -euo pipefail

WORKSPACE_DIR="${WORKSPACE_DIR:-/app}"
MODE_TO_RUN="${MODE_TO_RUN:-pod}"
OMNIPARSER_HOST="${OMNIPARSER_HOST:-0.0.0.0}"
OMNIPARSER_PORT="${OMNIPARSER_PORT:-8000}"

setup_ssh() {
    if [[ -z "${PUBLIC_KEY:-}" ]]; then
        return
    fi

    mkdir -p /root/.ssh /var/run/sshd
    echo "$PUBLIC_KEY" >> /root/.ssh/authorized_keys
    chmod 700 /root/.ssh
    chmod 600 /root/.ssh/authorized_keys
    ssh-keygen -A
    service ssh start
}

run_api() {
    cd "$WORKSPACE_DIR"
    exec python3 -m omnitool.omniparserserver.omniparserserver --host "$OMNIPARSER_HOST" --port "$OMNIPARSER_PORT"
}

run_handler() {
    cd "$WORKSPACE_DIR"
    exec python3 "$WORKSPACE_DIR/handler.py"
}

setup_ssh

case "$MODE_TO_RUN" in
    pod)
        run_api
        ;;
    serverless)
        run_handler
        ;;
    both)
        cd "$WORKSPACE_DIR"
        python3 -m omnitool.omniparserserver.omniparserserver --host "$OMNIPARSER_HOST" --port "$OMNIPARSER_PORT" &
        run_handler
        ;;
    *)
        echo "Unsupported MODE_TO_RUN: $MODE_TO_RUN"
        exit 1
        ;;
esac