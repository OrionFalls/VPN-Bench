#!/usr/bin/env bash
set -euo pipefail

REPO="https://github.com/OrionFalls/VPN-Bench.git"
INSTALL_DIR="${VPN_BENCH_DIR:-/opt/vpn-bench}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root."
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y ca-certificates git curl python3

if ! command -v docker >/dev/null 2>&1; then
  echo "Installing Docker Engine..."
  curl -fsSL https://get.docker.com | sh
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose plugin is unavailable."
  echo "Install the Docker Compose plugin and rerun this installer."
  exit 1
fi

if [[ -d "${INSTALL_DIR}/.git" ]]; then
  git -C "${INSTALL_DIR}" pull --ff-only
else
  mkdir -p "${INSTALL_DIR}"
  git clone "${REPO}" "${INSTALL_DIR}"
fi

cd "${INSTALL_DIR}"
mkdir -p data

if [[ ! -f config/config.yaml ]]; then
  cp config/config.example.yaml config/config.yaml
fi

if [[ ! -f .env ]]; then
  echo "Generating application encryption secret..."
  SECRET="$(python3 -c 'import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())')"
  umask 077
  printf 'VPN_BENCH_SECRET=%s
' "${SECRET}" > .env
fi

chmod 600 .env

docker compose up -d --build

echo "Waiting for VPN-Bench..."
for _ in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8080/health >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! curl -fsS http://127.0.0.1:8080/health >/dev/null 2>&1; then
  echo "VPN-Bench did not become healthy."
  docker compose ps
  docker compose logs --tail=80
  exit 1
fi

VM_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
VM_IP="${VM_IP:-127.0.0.1}"

echo
echo "========================================"
echo " VPN-Bench installation completed"
echo "========================================"
echo
echo "Web interface:"
echo "  http://${VM_IP}:8080/"
echo
echo "Health:"
echo "  http://${VM_IP}:8080/health"
echo
echo "Open the web interface to create the administrator account."
echo
