from vpn_bench.adapters.singbox import build_config


def test_xhttp_requires_extended_transport():
    uri = (
        "vless://00000000-0000-0000-0000-000000000001@example.com:443"
        "?type=xhttp&security=reality&sni=example.com&pbk=publickey&sid=1234#test"
    )
    try:
        build_config(uri)
    except RuntimeError as exc:
        assert "XHTTP" in str(exc)
    else:
        raise AssertionError("XHTTP must not be silently mapped to another transport")


def test_vless_tls_ws_config():
    uri = "vless://00000000-0000-0000-0000-000000000001@example.com:443?type=ws&security=tls&sni=edge.example.com&path=%2Fvpn#test"
    config = build_config(uri)
    outbound = config["outbounds"][0]
    assert outbound["type"] == "vless"
    assert outbound["tls"]["server_name"] == "edge.example.com"
    assert outbound["transport"]["type"] == "ws"
    assert outbound["transport"]["path"] == "/vpn"


def test_trojan_config():
    uri = "trojan://secret@example.com:443?security=tls&sni=example.com#test"
    outbound = build_config(uri)["outbounds"][0]
    assert outbound["type"] == "trojan"
    assert outbound["password"] == "secret"
    assert outbound["tls"]["server_name"] == "example.com"


def test_vless_xhttp_is_available_for_extended_core():
    uri = "vless://00000000-0000-0000-0000-000000000001@example.com:443?type=xhttp&security=reality&sni=example.com&pbk=publickey&sid=1234&mode=auto&path=%2Fx#test"
    outbound = build_config(uri, allow_extended_transports=True)["outbounds"][0]
    assert outbound["transport"]["type"] == "xhttp"
    assert outbound["transport"]["mode"] == "auto"
    assert outbound["transport"]["path"] == "/x"

from vpn_bench.subscription import parse_subscription


def test_extended_uri_schemes_are_normalized():
    items = parse_subscription(
        "tuic://00000000-0000-0000-0000-000000000001:pass@example.com:443#tuic\n"
        "anytls://pass@example.com:443#anytls\n"
        "ssh://user:pass@example.com:22#ssh\n"
        "socks5://user:pass@example.com:1080#socks\n"
        "naive+https://user:pass@example.com:443#naive"
    )
    assert [item.protocol for item in items] == ["tuic", "anytls", "ssh", "socks5", "naiveproxy"]



def test_tuic_config():
    uri = "tuic://00000000-0000-0000-0000-000000000001:secret@example.com:443?congestion_control=bbr&udp_relay_mode=native#test"
    outbound = build_config(uri, allow_extended_transports=True)["outbounds"][0]
    assert outbound["type"] == "tuic"
    assert outbound["uuid"].endswith("0001")
    assert outbound["congestion_control"] == "bbr"


def test_anytls_config():
    uri = "anytls://secret@example.com:443?security=tls&sni=example.com#test"
    outbound = build_config(uri, allow_extended_transports=True)["outbounds"][0]
    assert outbound["type"] == "anytls"
    assert outbound["password"] == "secret"


def test_naive_config():
    uri = "naive+https://user:secret@example.com:443#test"
    outbound = build_config(uri, allow_extended_transports=True)["outbounds"][0]
    assert outbound["type"] == "naive"
    assert outbound["username"] == "user"
    assert outbound["password"] == "secret"


def test_upstream_protocol_uses_udp_for_quic_protocols():
    from vpn_bench.adapters.singbox import _upstream_protocol

    assert _upstream_protocol("hysteria2://example.com:443") == "udp"
    assert _upstream_protocol("tuic://uuid:pass@example.com:443") == "udp"
    assert _upstream_protocol("vless://uuid@example.com:443?type=quic") == "udp"
    assert _upstream_protocol("vless://uuid@example.com:443?type=ws") == "tcp"


def test_upstream_protocol_defaults_to_tcp():
    from vpn_bench.adapters.singbox import _upstream_protocol

    assert _upstream_protocol("vless://uuid@example.com:443") == "tcp"
