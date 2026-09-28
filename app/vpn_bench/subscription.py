"""Subscription fetching and normalization.

This module does not establish VPN connections. It turns common subscription
formats into the application's normalized server model.
"""

from __future__ import annotations

import base64
import json
import re
import ipaddress
import socket
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any
from uuid import NAMESPACE_URL, uuid5


SUPPORTED_SCHEMES = {
    "vless",
    "vmess",
    "trojan",
    "ss",
    "shadowsocks",
    "hysteria2",
    "hy2",
    "tuic",
    "anytls",
    "ssh",
    "socks5",
    "socks",
    "naive+https",
    "naive+quic",
    "naive",
    "wireguard",
    "awg",
    "amneziawg",
    "masque",
}


@dataclass(frozen=True)
class ImportedServer:
    id: str
    name: str
    protocol: str
    host: str | None
    port: int | None
    transport: str | None
    security: str | None
    raw: dict[str, Any]


class SubscriptionError(RuntimeError):
    pass


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_subscription_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _validate_subscription_url(url: str) -> None:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme.lower() not in {"https", "http"}:
        raise SubscriptionError("Subscription URL must use HTTP or HTTPS")
    if not parsed.hostname:
        raise SubscriptionError("Subscription URL has no hostname")
    if parsed.username or parsed.password:
        raise SubscriptionError("Subscription URL must not contain credentials")

    try:
        addresses = {
            ipaddress.ip_address(item[4][0])
            for item in socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
        }
    except socket.gaierror as exc:
        raise SubscriptionError(f"Unable to resolve subscription host: {exc}") from exc

    for address in addresses:
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        ):
            raise SubscriptionError("Subscription URL resolves to a private or local address")


def fetch_subscription(url: str, timeout: float = 20.0) -> tuple[str, dict[str, str]]:
    _validate_subscription_url(url)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "VPN-Bench/0.2",
            "Accept": "*/*",
        },
    )
    opener = urllib.request.build_opener(_SafeRedirectHandler)
    try:
        with opener.open(request, timeout=timeout) as response:
            _validate_subscription_url(response.geturl())
            body = response.read(4 * 1024 * 1024 + 1)
            if len(body) > 4 * 1024 * 1024:
                raise SubscriptionError("Subscription is larger than the 4 MiB limit")
            headers = {k.lower(): v for k, v in response.headers.items()}
    except SubscriptionError:
        raise
    except Exception as exc:
        raise SubscriptionError(f"Unable to fetch subscription: {exc}") from exc
    return body.decode("utf-8-sig", errors="replace"), headers


def decode_subscription(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return ""

    if cleaned.startswith("{") or cleaned.startswith("["):
        return cleaned

    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    if any(re.match(r"^(?:[a-zA-Z][a-zA-Z0-9+.-]*):", line) for line in lines):
        return "\n".join(lines)

    compact = re.sub(r"\s+", "", cleaned)
    padded = compact + "=" * (-len(compact) % 4)
    try:
        decoded = base64.b64decode(padded, validate=True).decode("utf-8-sig")
    except Exception:
        return cleaned
    return decoded.strip() or cleaned


def parse_subscription(text: str) -> list[ImportedServer]:
    decoded = decode_subscription(text)
    if not decoded:
        return []

    if "[Interface]" in decoded and "PrivateKey" in decoded:
        return [_parse_wireguard_conf(decoded)]

    if decoded.startswith("{") or decoded.startswith("["):
        try:
            data = json.loads(decoded)
        except json.JSONDecodeError as exc:
            raise SubscriptionError(f"Invalid JSON subscription: {exc}") from exc
        return parse_json(data)

    result: list[ImportedServer] = []
    for line in decoded.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        server = parse_uri(line)
        if server:
            result.append(server)
    return result


def _parse_wireguard_conf(text: str) -> ImportedServer:
    section = ""
    interface: dict[str, list[str]] = {}
    peers: list[dict[str, list[str]]] = []
    current_peer: dict[str, list[str]] | None = None

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip().lower()
            if section == "peer":
                current_peer = {}
                peers.append(current_peer)
            continue
        if "=" not in line:
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        target = interface if section == "interface" else current_peer
        if target is not None:
            target.setdefault(key.lower(), []).append(value)

    if not interface.get("privatekey") or not interface.get("address") or not peers:
        raise SubscriptionError("Invalid WireGuard configuration")

    normalized_peers: list[dict[str, Any]] = []
    first_host = None
    first_port = None
    for peer in peers:
        endpoint = peer.get("endpoint", [None])[0]
        public_key = peer.get("publickey", [None])[0]
        if not endpoint or not public_key:
            continue
        parsed_endpoint = urllib.parse.urlsplit("//" + endpoint)
        host = parsed_endpoint.hostname
        port = parsed_endpoint.port
        if not host or not port:
            raise SubscriptionError(f"Invalid WireGuard endpoint: {endpoint}")
        first_host = first_host or host
        first_port = first_port or port
        normalized_peers.append(
            {
                "address": host,
                "port": port,
                "public_key": public_key,
                "pre_shared_key": (peer.get("presharedkey") or [None])[0],
                "allowed_ips": [
                    item.strip()
                    for item in ",".join(peer.get("allowedips", [])).split(",")
                    if item.strip()
                ],
                "persistent_keepalive_interval": (peer.get("persistentkeepalive") or [None])[0],
            }
        )

    if not normalized_peers:
        raise SubscriptionError("WireGuard configuration contains no usable peers")

    raw: dict[str, Any] = {
        "private_key": interface["privatekey"][0],
        "address": interface["address"],
        "peers": normalized_peers,
    }
    return ImportedServer(
        id=_server_id(text),
        name=str(first_host or "WireGuard"),
        protocol="wireguard",
        host=first_host,
        port=first_port,
        transport="udp",
        security=None,
        raw=raw,
    )


def parse_uri(uri: str) -> ImportedServer | None:
    if uri.lower().startswith("vmess://"):
        return _parse_vmess_uri(uri)

    parsed = urllib.parse.urlsplit(uri)
    scheme = parsed.scheme.lower()
    if scheme not in SUPPORTED_SCHEMES:
        return None

    query = urllib.parse.parse_qs(parsed.query)
    name = urllib.parse.unquote(parsed.fragment) or parsed.hostname or "Unnamed server"
    host = parsed.hostname
    port = parsed.port
    transport = _first(query, "type") or _first(query, "network")
    security = _first(query, "security")
    username = urllib.parse.unquote(parsed.username or "")
    password = urllib.parse.unquote(parsed.password or "")

    if scheme == "vless":
        transport = transport or "tcp"
    elif scheme == "trojan":
        transport = transport or "tcp"
        security = security or "tls"
    elif scheme in {"hysteria2", "hy2"}:
        transport = transport or "udp"
        security = security or "tls"
    elif scheme in {"ss", "shadowsocks"}:
        transport = transport or "tcp"
    elif scheme in {"socks5", "socks"}:
        transport = transport or "tcp"
    elif scheme in {"anytls", "naive", "naive+https", "naive+quic"}:
        transport = transport or ("quic" if scheme == "naive+quic" else "tcp")
        security = security or "tls"
    elif scheme == "ssh":
        transport = transport or "tcp"
    elif scheme in {"wireguard", "awg", "amneziawg"}:
        transport = transport or "udp"
    elif scheme == "masque":
        transport = transport or "quic"
        security = security or "tls"

    return ImportedServer(
        id=_server_id(uri),
        name=name,
        protocol=_normalize_protocol(scheme),
        host=host,
        port=port,
        transport=transport,
        security=security,
        raw={
            "uri": uri,
            "query": query,
            "username": username,
            "password": password,
        },
    )


def _parse_vmess_uri(uri: str) -> ImportedServer | None:
    encoded = uri.split("://", 1)[1]
    try:
        padded = encoded + "=" * (-len(encoded) % 4)
        data = json.loads(base64.b64decode(padded).decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or not data.get("add"):
        return None
    transport = str(data.get("net") or "tcp").lower()
    security = "tls" if str(data.get("tls") or "").lower() == "tls" else None
    name = str(data.get("ps") or data.get("add"))
    return ImportedServer(
        id=_server_id(uri),
        name=name,
        protocol="vmess",
        host=str(data["add"]),
        port=_safe_int(data.get("port")),
        transport=transport,
        security=security,
        raw=data,
    )


def parse_json(data: Any) -> list[ImportedServer]:
    if isinstance(data, dict) and isinstance(data.get("outbounds"), list):
        return _parse_sing_box_outbounds(data["outbounds"])

    if isinstance(data, dict) and isinstance(data.get("endpoints"), list):
        return _parse_sing_box_endpoints(data["endpoints"])

    if isinstance(data, list):
        result: list[ImportedServer] = []
        for item in data:
            if isinstance(item, str):
                parsed = parse_uri(item)
                if parsed:
                    result.append(parsed)
            elif isinstance(item, dict):
                result.extend(_parse_sing_box_outbounds([item]))
        return result

    raise SubscriptionError("Unsupported JSON subscription format")


def _parse_sing_box_outbounds(outbounds: list[Any]) -> list[ImportedServer]:
    result: list[ImportedServer] = []
    supported_json_types = {
        "vless", "vmess", "trojan", "shadowsocks", "ss", "hysteria2",
        "tuic", "anytls", "socks", "http", "naive", "wireguard",
    }
    for index, item in enumerate(outbounds):
        if not isinstance(item, dict):
            continue
        protocol = str(item.get("type", "")).lower()
        if protocol not in supported_json_types:
            continue

        host = item.get("server")
        port = _safe_int(item.get("server_port"))
        tls = item.get("tls") if isinstance(item.get("tls"), dict) else {}
        transport_data = item.get("transport") if isinstance(item.get("transport"), dict) else {}
        transport = transport_data.get("type")
        if protocol in {"hysteria2", "tuic"} and not transport:
            transport = "udp"
        if protocol == "naive" and not transport:
            transport = "quic" if item.get("quic") else "tcp"
        if protocol in {"wireguard"} and not transport:
            transport = "udp"

        security = "tls" if tls.get("enabled") else None
        name = str(item.get("tag") or host or f"Server {index + 1}")
        raw = dict(item)
        result.append(
            ImportedServer(
                id=_server_id(json.dumps(item, sort_keys=True)),
                name=name,
                protocol=_normalize_protocol(protocol),
                host=str(host) if host else None,
                port=port,
                transport=str(transport) if transport else None,
                security=security,
                raw=raw,
            )
        )
    return result


def _parse_sing_box_endpoints(endpoints: list[Any]) -> list[ImportedServer]:
    result: list[ImportedServer] = []
    for index, item in enumerate(endpoints):
        if not isinstance(item, dict):
            continue
        endpoint_type = str(item.get("type", "")).lower()
        if endpoint_type not in {"wireguard", "amnezia_wg", "amneziawg"}:
            continue
        peers = item.get("peers")
        peer = peers[0] if isinstance(peers, list) and peers and isinstance(peers[0], dict) else {}
        host = peer.get("server") or peer.get("address") or item.get("server")
        port = _safe_int(peer.get("server_port") or item.get("server_port") or 51820)
        raw = dict(item)
        raw["peer"] = peer
        result.append(
            ImportedServer(
                id=_server_id(json.dumps(item, sort_keys=True)),
                name=str(item.get("tag") or host or f"Endpoint {index + 1}"),
                protocol="amneziawg" if "amnezia" in endpoint_type else "wireguard",
                host=str(host) if host else None,
                port=port,
                transport="udp",
                security=None,
                raw=raw,
            )
        )
    return result


def _normalize_protocol(scheme: str) -> str:
    return {
        "hy2": "hysteria2",
        "ss": "shadowsocks",
        "shadowsocks": "shadowsocks",
        "socks": "socks5",
        "naive": "naiveproxy",
        "naive+https": "naiveproxy",
        "naive+quic": "naiveproxy",
        "awg": "amneziawg",
        "amneziawg": "amneziawg",
    }.get(scheme, scheme)


def _server_id(value: str) -> str:
    return uuid5(NAMESPACE_URL, value).hex


def _first(values: dict[str, list[str]], key: str) -> str | None:
    value = values.get(key)
    return value[0] if value else None


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
