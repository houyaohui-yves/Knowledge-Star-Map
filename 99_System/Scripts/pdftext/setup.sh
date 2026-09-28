#!/bin/sh
set -eu
TOOL_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHON=${PDFTEXT_PYTHON:-python3}
"$PYTHON" -c 'import sys; assert sys.version_info >= (3, 12), "当前固定依赖需要 Python 3.12 或更高版本（已验证 3.12）"'
"$PYTHON" -m venv "$TOOL_DIR/.venv"
"$TOOL_DIR/.venv/bin/python" -m pip install -r "$TOOL_DIR/requirements.txt"
"$TOOL_DIR/pdftext" doctor --download-models
