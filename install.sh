#!/usr/bin/env bash
set -euo pipefail

REPO="https://github.com/OrionFalls/VPN-Bench.git"
INSTALL_DIR="${VPN_BENCH_DIR:-/opt/vpn-bench}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: curl ... | sudo bash"
  exit 1
fi

command -v git >/dev/null 2>&1 || {
  apt-get update
  apt-get install -y git ca-certificates
}

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed. Install Docker Engine first."
  echo "See: https://docs.docker.com/engine/install/"
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
