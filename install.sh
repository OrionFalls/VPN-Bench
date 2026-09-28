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
apt-get install -y ca-certificates git curl

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

docker compose up -d --build

echo
echo "VPN-Bench is installed."
echo "Directory: ${INSTALL_DIR}"
echo "Web UI/API: http://<VM-IP>:8080/"
echo "Health:     http://<VM-IP>:8080/health"
