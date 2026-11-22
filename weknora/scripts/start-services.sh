#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
mkdir -p .local
export HOST_BRIDGE_IP="$(docker network inspect bridge --format '{{(index .IPAM.Config 0).Gateway}}')"
if ! curl -fsS --max-time 2 http://127.0.0.1:18083/health >/dev/null; then
  nohup .local/venv/bin/python scripts/model_gateway.py > .local/model-gateway.log 2>&1 < /dev/null &
  echo $! > .local/model-gateway.pid
fi
if ! curl -fsS --max-time 2 http://127.0.0.1:18084/health >/dev/null; then
  pdf_python=.local/venv/bin/python
  if ! "$pdf_python" -c 'import pydantic, pypdfium2' >/dev/null 2>&1; then
    pdf_python=/usr/bin/python3
  fi
  nohup "$pdf_python" scripts/pdf_reader.py > .local/pdf-reader.log 2>&1 < /dev/null &
  echo $! > .local/pdf-reader.pid
fi
