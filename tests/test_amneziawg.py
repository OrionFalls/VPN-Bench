import json

from vpn_bench.adapters.wireguard import build_amneziawg_config
from vpn_bench.subscription import parse_subscription


def test_parse_amneziawg_uri():
    uri = (
        "awg://PRIVATEKEY@example.com:51820"
        "?publickey=SERVERKEY&address=10.8.1.2%2F32"
        "&jc=4&jmin=40&jmax=70&s1=0&s2=0"
        "&h1=123&h2=124&h3=125&h4=126&i1=%3Cb%200x01%3E%3Cr%2012%3E"
        "#test"
    )
    server = parse_subscription(uri)[0]

    assert server.protocol == "amneziawg"
    assert server.host == "example.com"
    assert server.raw["private_key"] == "PRIVATEKEY"
    assert server.raw["address"] == ["10.8.1.2/32"]
    assert server.raw["peers"][0]["public_key"] == "SERVERKEY"
    assert server.raw["jc"] == 4
    assert server.raw["h1"] == 123
    assert server.raw["i1"] == "<b 0x01><r 12>"


def test_build_amneziawg_config_keeps_endpoint_fields():
    config = json.loads(build_amneziawg_config({
        "private_key": "PRIVATEKEY",
        "address": ["10.8.1.2/32"],
        "peers": [{
            "address": "example.com",
            "port": 51820,
            "public_key": "SERVERKEY",
            "allowed_ips": ["0.0.0.0/0"],
        }],
        "jc": 4,
        "jmin": 40,
        "jmax": 70,
        "s4": 12,
        "h1": "100-200",
        "i1": "<b 0x01><r 12>",
    }, 18080))

    endpoint = config["endpoints"][0]
    assert endpoint["type"] == "wireguard"
    assert endpoint["system"] is False
    assert endpoint["jc"] == 4
    assert endpoint["h1"] == "100-200"
    assert endpoint["i1"] == "<b 0x01><r 12>"
    assert config["route"]["final"] == "awg-endpoint"
