#!/usr/bin/env python3
"""Generate private local settings without overwriting any existing files."""
import json
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def create(relative, content):
    p = ROOT / relative
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        print('Kept:', relative)
        return
    with p.open('x') as f:
        p.chmod(0o600)
        f.write(content)
    print('Created:', relative)

we = (ROOT / 'deploy/weknora.env.example').read_text()
we = we.replace('GENERATE_AES_KEY', secrets.token_hex(16)).replace('GENERATE_JWT_SECRET', secrets.token_hex(32))
create('weknora/.local/weknora.env', we)
create('weknora/.local/secrets/opencode-go.key', 'REPLACE_WITH_OPENCODE_GO_KEY\n')
create('weknora/datasheets/manifest.json', (ROOT / 'weknora/datasheets/manifest.example.json').read_text())
create('deerflow-deploy/config.yaml', (ROOT / 'deerflow-deploy/config.example.yaml').read_text())
# One shared secret for the two services; on rerun recover it from an existing file.
secret = secrets.token_urlsafe(48)
for rel in ('.local/deerflow-runtime/runtime.env', '.local/deerflow-runtime/frontend.env'):
    p = ROOT / rel
    if p.exists():
        for line in p.read_text().splitlines():
            if line.startswith('BETTER_AUTH_SECRET='):
                secret = line.split('=', 1)[1]
create('.local/deerflow-runtime/runtime.env', '\n'.join([
    'OPENCODE_GO_API_KEY=REPLACE_WITH_OPENCODE_GO_KEY',
    'WEKNORA_API_KEY=REPLACE_WITH_WEKNORA_API_KEY',
    'BETTER_AUTH_SECRET=' + secret,
    'DEER_FLOW_INTERNAL_AUTH_TOKEN=' + secrets.token_urlsafe(48),
    'LANGSMITH_TRACING=false', 'DEER_FLOW_DATE_TIMEZONE=Asia/Shanghai',
    'DEERFLOW_PUBLIC_URL=http://localhost:2026', 'WEKNORA_PUBLIC_URL=http://localhost:18088',
    'NO_PROXY=localhost,127.0.0.1,::1,gateway,frontend,nginx,redis,chatbot-weknora-app-1,host.docker.internal', ''
]))
create('.local/deerflow-runtime/frontend.env', 'BETTER_AUTH_SECRET=' + secret + '\n')
create('.local/deerflow-runtime/extensions_config.json', '{"mcpServers": {}}\n')
create('.local/deerflow-runtime/pdf-catalog/catalog.json', '[]\n')
(ROOT / '.local/deerflow-runtime/data').mkdir(parents=True, exist_ok=True)
print('Edit the generated key files before starting; see docs/deployment.md.')
