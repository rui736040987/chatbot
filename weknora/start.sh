#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
if ! docker info >/dev/null 2>&1; then
  if [[ -x /mnt/c/Windows/System32/wsl.exe ]]; then
    /mnt/c/Windows/System32/wsl.exe -d "${WSL_DISTRO_NAME:-Ubuntu-24.04}" -u root -- service docker start
  else
    sudo service docker start
  fi
fi
# Start WSL host adapters independently of the invoking terminal.
if [[ -x /mnt/c/Windows/System32/wsl.exe ]]; then
  /mnt/c/Windows/System32/wsl.exe -d "${WSL_DISTRO_NAME:-Ubuntu-24.04}" -u "$(id -un)" -- /usr/bin/setsid -f "$PWD/scripts/start-services.sh"
else
  setsid -f "$PWD/scripts/start-services.sh"
fi
for attempt in {1..30}; do
  if curl -fsS --max-time 2 http://127.0.0.1:18083/health >/dev/null && curl -fsS --max-time 2 http://127.0.0.1:18084/health >/dev/null; then break; fi
  sleep 1
done
curl -fsS --max-time 3 http://127.0.0.1:18083/health >/dev/null
curl -fsS --max-time 3 http://127.0.0.1:18084/health >/dev/null
docker compose up -d --wait
printf '\nWeKnora: http://localhost:18088\nLogin: .local/login.json\n'
