#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
../weknora/start.sh
if [[ ! -f ../.local/deerflow-runtime/pdf-catalog/catalog.json ]]; then
  python3 build_pdf_catalog.py
fi
docker compose up -d --wait --wait-timeout 240
printf '\nDeerFlow: http://localhost:2026\n'
