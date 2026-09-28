# ⚡ VPN-Bench

<div align="center">

<img src="assets/logo.svg" alt="VPN-Bench" width="190">

### Real-world VPN server benchmarking

**Import subscriptions → screen bad nodes → test the best → build long-term history.**

[![CI](https://github.com/OrionFalls/VPN-Bench/actions/workflows/ci.yml/badge.svg)](https://github.com/OrionFalls/VPN-Bench/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.13%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-GPL--3.0-blue)](LICENSE)

[🇷🇺 Русский](README.md) · 🇬🇧 **English**

</div>

> 🧪 **Status:** active development. The core architecture and runtime are working; measurement methodology and analytics are still evolving.

---

## 🎯 Why VPN-Bench?

A typical speed test answers:

**“How fast is it right now?”**

VPN-Bench is designed to answer:

> **“How does this VPN node behave in real network conditions — and how does it behave tomorrow?”**

Instead of relying on a single ping to the VPN endpoint, traffic is tested through a **real VPN connection inside an isolated network namespace**.

![VPN-Bench architecture](https://raw.githubusercontent.com/OrionFalls/VPN-Bench/main/assets/readme/architecture-en.svg)

---

## ✨ What's here

| | Capability |
|---|---|
| 🔐 | Admin setup, authentication and sessions |
| 🔗 | VPN provider subscriptions |
| 🔄 | Subscription synchronization |
| 📦 | Normalized server model |
| 🧩 | VLESS · VMess · Trojan · Shadowsocks · Hysteria2 · TUIC · AnyTLS · SSH · SOCKS5 · NaiveProxy |
| 🗂️ | Base64 subscriptions and sing-box JSON |
| 🧠 | Runtime capability detection |
| 🧪 | Fast screening before long tests |
| 📡 | DNS · TCP/TLS · HTTP/HTTPS |
| 📊 | Latency · jitter · packet loss |
| 🚀 | Throughput samples |
| 🛡️ | Separate whitelist-sensitive target checks |
| 📈 | Measurement history and analytics foundation |
| 🐳 | Docker deployment |
| 🧱 | Isolated privileged worker |
| ❤️ | Healthchecks and CI |

### VPN runtime

**LX → Extended → WireGuard → optional Xray**

- **sing-box-lx** — primary runtime;
- **sing-box-extended** — extended fallback;
- **WireGuard** — dedicated standard adapter;
- **Xray** — optional compatibility backend.

---

## 🧪 How a benchmark works

![Benchmark flow](https://raw.githubusercontent.com/OrionFalls/VPN-Bench/main/assets/readme/benchmark-flow-en.svg)

### 1. 📥 Import

A provider subscription is parsed into a normalized server list.

### 2. ⚡ Screening

Short passes quickly remove nodes that fail connection or basic network checks.

### 3. 🔬 Full test

Only selected servers proceed to longer measurements.

### 4. 📊 History

Measurements are stored so node behaviour can be compared over time.

---

## 🛡️ Isolation first

A VPN test **must not break VPN-Bench's own network**.

The Controller runs without `NET_ADMIN`.

The Worker creates a separate Linux network namespace for each job:

```text
Controller
    │
    ▼
Worker
    │
    ├── Job #1 → netns → VPN → probes
    ├── Job #2 → netns → VPN → probes
    └── Job #3 → netns → VPN → probes
```

VPN cores and TUN interfaces remain inside the namespace.

---

## 🎯 Whitelist-bypass

Whitelist testing is a separate measurement, not another ping.

```text
Target
  │
  ├── without VPN → reachable?
  │       └── yes → not_applicable
  │
  └── without VPN → blocked
          │
          └── through VPN → reachable?
                  ├── yes → bypass confirmed
                  └── no → failed
```

This keeps ordinary Internet availability separate from whitelist-bypass results.

---

## ⏱️ Test modes

### ⚖️ Equal Time

The total campaign duration is distributed across selected servers.

**Example:** 20 servers × 60 seconds ≈ 20 minutes.

### ▶️ Sequential

Servers are tested one after another.

---

## 🖥️ Web UI

| Section | Purpose |
|---|---|
| 🏠 **Dashboard** | system state and current campaign |
| 🔗 **Providers** | subscriptions and synchronization |
| 🖥️ **Servers** | imported nodes and capabilities |
| 🧪 **Tests** | screening and full tests |
| 📊 **Analytics** | accumulated measurements |
| 📜 **Logs** | diagnostics |
| ⚙️ **Settings** | system settings |

Desktop, tablet and mobile layouts are supported.

---

## 🚀 Quick start

A dedicated Debian/Ubuntu VM is recommended.

```bash
curl -fsSL https://raw.githubusercontent.com/OrionFalls/VPN-Bench/main/install.sh | sudo bash
```

The installer:

1. installs Docker when required;
2. clones or updates the repository;
3. creates configuration;
4. generates the secret;
5. builds the containers;
6. starts Controller + Worker;
7. waits for healthchecks;
8. prints the Web UI address.

> 💡 For production, use a dedicated VM/LXC rather than installing VPN-Bench directly on the main OpenWrt router.

---

## 🧱 Architecture

```text
                  ┌─────────────────────┐
                  │       Web UI        │
                  │       FastAPI       │
                  └──────────┬──────────┘
                             │
                  ┌──────────▼──────────┐
                  │     Controller      │
                  │     SQLite / API    │
                  └──────────┬──────────┘
                             │
                  Docker internal network
                             │
                  ┌──────────▼──────────┐
                  │       Worker        │
                  │ NET_ADMIN + TUN     │
                  └──────────┬──────────┘
                             │
                    isolated netns
                             │
              ┌──────────────▼──────────────┐
              │        VPN runtime         │
              │ LX / Extended / WG / Xray  │
              └──────────────┬──────────────┘
                             │
                    real test traffic
                             │
              ┌──────────────▼──────────────┐
              │ DNS · HTTP · TCP · Speed    │
              │ Latency · Loss · Bypass     │
              └─────────────────────────────┘
```

---

## 🔒 Security

- Subscription URLs are encrypted at rest.
- The encryption key is supplied through `VPN_BENCH_SECRET`.
- The Controller does not receive `NET_ADMIN`.
- VPN sessions run in isolated network namespaces.
- External access should use HTTPS reverse proxy + firewall restrictions.

---

## 🛠️ Development

```bash
git clone https://github.com/OrionFalls/VPN-Bench.git
cd VPN-Bench

pip install -e .
pytest -q
```

Docker:

```bash
docker compose up -d --build
```

CI checks the Python test suite, browser JavaScript and Docker image build.

---

## 🗺️ Roadmap

- [x] Controller / Worker architecture
- [x] Isolated VPN runtime
- [x] Provider subscriptions
- [x] Server normalization
- [x] Basic network probes
- [x] Screening campaigns
- [x] Responsive UI
- [ ] 📈 Full analytics and charts
- [ ] 🚀 Controlled throughput benchmark
- [ ] 🛡️ Extended whitelist-bypass benchmark
- [ ] 🕐 Long-term stability campaigns
- [ ] 🗄️ PostgreSQL backend
- [ ] 📤 Result export
- [ ] 🔔 Degradation alerts

---

## 🤝 Project idea

VPN-Bench is being built as a **reproducible VPN testing laboratory**, not another one-shot speed test.

Fixed targets → consistent methodology → isolated execution → raw measurements → history.

**Less guesswork. More data.**

---

<div align="center">

**⚡ VPN-Bench**

[GitHub](https://github.com/OrionFalls/VPN-Bench) · GPL-3.0

</div>
