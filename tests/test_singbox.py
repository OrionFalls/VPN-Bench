from vpn_bench.adapters.singbox import build_config


def test_vless_reality_xhttp_is_rejected_by_upstream_singbox():
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
