"""Capability detection for VPN-Bench runtime cores.

The matrix is deliberately conservative: "supported" means that the current
adapter can actually build a connection configuration, not merely that a
third-party core claims support for the protocol.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CoreCapability:
    core: str
    supported: bool
    reason: str


# What our current adapters can generate, not the full upstream protocol list.
LX_PROTOCOLS = {"vless", "vmess", "trojan", "ss", "shadowsocks", "hysteria2", "hy2"}
LX_TRANSPORTS = {"tcp", "ws", "websocket", "grpc", "http", "httpupgrade", "quic", "xhttp"}

EXTENDED_PROTOCOLS = {
    "vless", "vmess", "trojan", "ss", "shadowsocks", "hysteria2", "hy2",
    "tuic", "anytls", "ssh", "masque", "mieru", "trusttunnel",
}
EXTENDED_TRANSPORTS = LX_TRANSPORTS

XRAY_PROTOCOLS = {"vless"}
XRAY_TRANSPORTS = {"tcp", "raw", "ws", "websocket", "grpc", "xhttp", "httpupgrade"}


def detect_capabilities(protocol: str | None, transport: str | None) -> tuple[CoreCapability, ...]:
    protocol = (protocol or "").lower()
    transport = (transport or "tcp").lower()

    result: list[CoreCapability] = []

    lx = protocol in LX_PROTOCOLS and transport in LX_TRANSPORTS
    result.append(CoreCapability(
        "sing-box-lx",
        lx,
        "supported by the current LX adapter" if lx else "protocol/transport is outside the current LX adapter",
    ))

    extended = protocol in EXTENDED_PROTOCOLS and transport in EXTENDED_TRANSPORTS
    result.append(CoreCapability(
        "sing-box-extended",
        extended,
        "supported by the current Extended adapter" if extended else "requires an adapter/config generator not implemented yet",
    ))

    xray = protocol in XRAY_PROTOCOLS and transport in XRAY_TRANSPORTS
    result.append(CoreCapability(
        "xray",
        xray,
        "supported by the Xray compatibility adapter" if xray else "not supported by the current Xray adapter",
    ))

    return tuple(result)


def preferred_cores(protocol: str | None, transport: str | None) -> tuple[str, ...]:
    return tuple(item.core for item in detect_capabilities(protocol, transport) if item.supported)
