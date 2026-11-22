#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
docker compose stop
for service in model-gateway pdf-reader; do
  pidfile=".local/$service.pid"
  if [[ -f "$pidfile" ]]; then
    pid="$(cat "$pidfile")"
    if [[ "$pid" =~ ^[0-9]+$ ]] && [[ -r "/proc/$pid/cmdline" ]]; then
      cmd="$(tr '\0' ' ' < "/proc/$pid/cmdline")"
      if [[ "$cmd" == *scripts/model_gateway.py* || "$cmd" == *scripts/pdf_reader.py* ]]; then kill -TERM "$pid"; fi
    fi
  fi
done
