#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
git submodule update --init --recursive
python3 scripts/init-local.py
python3 -m venv weknora/.local/venv
weknora/.local/venv/bin/python -m pip install -r deploy/requirements.txt
weknora/.local/venv/bin/python - <<'PY'
from pathlib import Path
from fastembed import TextEmbedding
TextEmbedding(model_name='BAAI/bge-small-zh-v1.5', cache_dir=str(Path('weknora/.local/model-cache').resolve()), threads=4)
print('Embedding model cached.')
PY
