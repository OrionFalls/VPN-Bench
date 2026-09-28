from vpn_bench.adapters.xray import build_config


def test_vless_xhttp_reality_config():
    uri = (
        "vless://00000000-0000-0000-0000-000000000001@example.com:443"
        "?type=xhttp&security=reality&sni=example.com&fp=chrome"
        "&pbk=public-key&sid=1234&path=%2Fedge&mode=auto#test"
    )
    config = build_config(uri)
    outbound = config["outbounds"][0]
    assert outbound["protocol"] == "vless"
    assert outbound["streamSettings"]["network"] == "xhttp"
    assert outbound["streamSettings"]["security"] == "reality"
    assert outbound["streamSettings"]["xhttpSettings"]["path"] == "/edge"
    assert outbound["streamSettings"]["realitySettings"]["publicKey"] == "public-key"
