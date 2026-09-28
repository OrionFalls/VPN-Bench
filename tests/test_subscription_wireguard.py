from vpn_bench.subscription import parse_subscription


def test_parse_wireguard_conf():
    servers = parse_subscription(
        """[Interface]
PrivateKey = PRIVATE
Address = 10.8.0.2/32

[Peer]
PublicKey = PUBLIC
Endpoint = vpn.example.com:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""
    )
    assert len(servers) == 1
    assert servers[0].protocol == "wireguard"
    assert servers[0].host == "vpn.example.com"
    assert servers[0].raw["private_key"] == "PRIVATE"
    assert servers[0].raw["peers"][0]["allowed_ips"] == ["0.0.0.0/0"]
