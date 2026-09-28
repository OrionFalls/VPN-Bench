from vpn_bench.subscription import decode_subscription, parse_subscription


def test_plain_vless_uri_is_normalized():
    servers = parse_subscription(
        "vless://uuid@example.com:443?type=xhttp&security=tls#My%20Server"
    )
    assert len(servers) == 1
    server = servers[0]
    assert server.name == "My Server"
    assert server.protocol == "vless"
    assert server.transport == "xhttp"
    assert server.security == "tls"
    assert server.port == 443


def test_base64_subscription_is_decoded():
    import base64

    source = "trojan://secret@example.com:443?security=tls#Test"
    encoded = base64.b64encode(source.encode()).decode()
    servers = parse_subscription(encoded)
    assert servers[0].protocol == "trojan"


def test_sing_box_outbounds_are_supported():
    servers = parse_subscription(
        '{"outbounds":[{"type":"vless","tag":"NL 01","server":"1.2.3.4","server_port":443,'
        '"tls":{"enabled":true},"transport":{"type":"xhttp"}},{"type":"direct","tag":"direct"}]}'
    )
    assert len(servers) == 1
    assert servers[0].name == "NL 01"
    assert servers[0].transport == "xhttp"
    assert servers[0].security == "tls"


def test_unknown_lines_are_ignored():
    assert parse_subscription("hello\nnot-a-vpn-uri\n") == []
    assert decode_subscription("") == ""
