#!/bin/sh
set -eu
cd "$(dirname "$0")"
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
export RESEARCHLENS_EXTERNAL_DIGEST_WORKER=1
PYTHON_BIN="${RESEARCHLENS_PYTHON:-.venv-py312/bin/python}"
if [ ! -x "$PYTHON_BIN" ]; then
  echo "找不到可执行的 Python：$PYTHON_BIN" >&2
  echo "请使用 Python 3.12 环境，或设置 RESEARCHLENS_PYTHON 指向其解释器。" >&2
  exit 1
fi
PORT="${RESEARCHLENS_PORT:-8501}"
"$PYTHON_BIN" digest_worker.py &
digest_pid=$!
cleanup() {
  kill "$digest_pid" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
"$PYTHON_BIN" -m streamlit run app.py --server.address 127.0.0.1 --server.port "$PORT" --server.headless true
