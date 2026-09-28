# Installation

VPN-Bench is designed to run independently from the user's main router.

## Supported deployment target

The recommended first deployment is a dedicated Debian VM or LXC with Docker.

## One-command installation

After Docker is installed:

```bash
curl -fsSL https://raw.githubusercontent.com/OrionFalls/VPN-Bench/main/install.sh | sudo bash
```

The default installation directory is `/opt/vpn-bench`.

Override it with:

```bash
VPN_BENCH_DIR=/srv/vpn-bench bash install.sh
```

## Configuration

Edit:

```text
/opt/vpn-bench/config/config.yaml
```

Do not commit real subscription URLs, credentials, or access tokens.

## Upgrade

Run the same installation command again. The installer pulls the latest `main` revision and rebuilds the container.

## Safety

The benchmark VM should have its own network path and must not depend on the production OpenWrt instance. VPN adapters will later run in isolated network namespaces/containers so a broken VPN configuration cannot alter the host's default route.
