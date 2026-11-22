#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
docker compose -f weknora/compose.yaml ps
docker compose -f deerflow-deploy/compose.yaml ps
