from vpn_bench.adapters.wireguard import build_wireguard_config


def test_build_wireguard_config():
    config = build_wireguard_config(
        {
            "private_key": "PRIVATE",
            "address": ["10.8.0.2/32"],
            "peers": [
                {
                    "address": "vpn.example.com",
                    "port": 51820,
                    "public_key": "PUBLIC",
                    "allowed_ips": ["0.0.0.0/0"],
                    "persistent_keepalive_interval": 25,
                }
            ],
        }
    )
    assert "PrivateKey = PRIVATE" in config
    assert "Address = 10.8.0.2/32" in config
    assert "PublicKey = PUBLIC" in config
    assert "Endpoint = vpn.example.com:51820" in config
    assert "AllowedIPs = 0.0.0.0/0" in config
