# VPN-Bench

Self-hosted automated VPN server benchmarking and long-term monitoring.

## Status

Early development. The repository starts with the architecture and MVP foundation.

## Goals

- Import VPN servers from provider subscriptions/configuration sources.
- Run isolated tests without touching the main home router.
- Measure real-world connectivity, DNS, HTTP(S), latency, packet loss, jitter, and throughput.
- Run short screening tests and longer stability campaigns.
- Keep raw measurements for later analysis.
- Provide a web dashboard and API.
- Keep VPN adapters separate from the benchmark engine so protocols are interchangeable.

## Planned architecture

```
Provider subscription
        |
        v
Server/config importer
        |
        v
VPN adapter / isolated connection
        |
        v
Universal benchmark engine
        |
        +--> DNS
        +--> HTTP(S)
        +--> latency / loss
        +--> jitter
        +--> throughput
        +--> stability
        |
        v
SQLite/PostgreSQL
        |
        v
Web UI / API
```

## MVP

The first milestone will provide:

1. Configuration for VPN providers/subscriptions.
2. A normalized server model.
3. A test runner interface.
4. Persisted test results.
5. Docker-based deployment.

VPN protocol adapters and automatic subscription parsing will be added incrementally.

## License

TBD.
