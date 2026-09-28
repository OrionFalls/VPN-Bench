"""Subscription fetching and normalization.

This module does not establish VPN connections. It only turns common
subscription formats into the application's normalized server model.
"""

from __future__ import annotations

import base64
import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any
from uuid import uuid5, NAMESPACE_URL


SUPPORTED_SCHEMES = {"vless","vmess","trojan","ss","hysteria2","hy2","tuic","anytls","ssh","socks5","socks","naive+https","naive+quic","wireguard","awg","masque"}


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


def fetch_subscription(url: str, timeout: float = 20.0) -> tuple[str, dict[str, str]]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "VPN-Bench/0.2",
            "Accept": "*/*",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(4 * 1024 * 1024)
            headers = {k.lower(): v for k, v in response.headers.items()}
    except Exception as exc:
        raise SubscriptionError(f"Unable to fetch subscription: {exc}") from exc
    return body.decode("utf-8-sig", errors="replace"), headers


def decode_subscription(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return ""

    # A JSON/sing-box document should remain JSON.
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
        security = security or _first(query, "security")
    elif scheme == "trojan":
        transport = transport or "tcp"
        security = security or "tls"
    elif scheme in {"hysteria2", "hy2"}:
        transport = transport or "udp"
        security = security or "tls"
    elif scheme == "ss":
        transport = transport or "tcp"
    elif scheme in {"socks5", "socks"}:
        transport = transport or "tcp"
    elif scheme in {"anytls", "naive+https", "naive+quic"}:
        transport = transport or ("quic" if scheme == "naive+quic" else "tcp")
        security = security or "tls"
    elif scheme == "ssh":
        transport = transport or "tcp"
    elif scheme in {"wireguard", "awg"}:
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
        raw={"uri": uri, "query": query, "username": username, "password": password},
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

    if isinstance(data, list):
        result = []
        for item in data:
            if isinstance(item, str):
                parsed = parse_uri(item)
                if parsed:
                    result.append(parsed)
        return result

    raise SubscriptionError("Unsupported JSON subscription format")


def _parse_sing_box_outbounds(outbounds: list[Any]) -> list[ImportedServer]:
    result: list[ImportedServer] = []
    for index, item in enumerate(outbounds):
        if not isinstance(item, dict):
            continue
        protocol = str(item.get("type", "")).lower()
        if protocol not in SUPPORTED_SCHEMES:
            continue
        host = item.get("server")
        port = _safe_int(item.get("server_port"))
        tls = item.get("tls") if isinstance(item.get("tls"), dict) else {}
        transport_data = item.get("transport") if isinstance(item.get("transport"), dict) else {}
        transport = transport_data.get("type")
        security = "tls" if tls.get("enabled") else None
        name = str(item.get("tag") or host or f"Server {index + 1}")
        result.append(
            ImportedServer(
                id=_server_id(json.dumps(item, sort_keys=True)),
                name=name,
                protocol="hysteria2" if protocol == "hy2" else protocol,
                host=str(host) if host else None,
                port=port,
                transport=str(transport) if transport else None,
                security=security,
                raw=item,
            )
        )
    return result


def _normalize_protocol(scheme: str) -> str:
    return {"hy2":"hysteria2","ss":"shadowsocks","socks":"socks5","naive+https":"naiveproxy","naive+quic":"naiveproxy","awg":"amneziawg"}.get(scheme, scheme)


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
