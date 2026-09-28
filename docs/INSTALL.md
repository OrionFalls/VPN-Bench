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


## First runtime check

The installer runs a privileged namespace self-test inside the worker after the containers become healthy. It verifies:

- creation and routing of a per-job Linux network namespace;
- connectivity to the worker-side veth;
- explicit kill-switch allow rules;
- blocking of an unlisted external destination;
- cleanup of the namespace and firewall state.

If this check fails, the installer stops instead of leaving a deployment that cannot safely isolate VPN traffic.

The worker requires `NET_ADMIN`, `SYS_ADMIN`, `/dev/net/tun`, and an unconfined seccomp profile because the current namespace implementation uses Linux network namespaces and veth devices.

## Benchmark configuration

The worker reads the same `config/config.yaml` as the controller. Configure normal HTTP targets, DNS test domain, optional controlled download/upload endpoints, throughput sample duration, and optional whitelist-sensitive targets there.

For throughput measurements, use a controlled endpoint where possible. Do not point the benchmark at an endpoint that you do not control for upload testing.

## Screening

The Tests page supports a short screening campaign before a long test. The first pass checks all selected active servers; subsequent passes are limited to survivors according to the screening policy. A completed screening can launch a full test using the resulting shortlist.
