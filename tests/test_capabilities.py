from vpn_bench.capabilities import preferred_cores


def test_preferred_cores_deduplicates_amneziawg():
    assert preferred_cores("amneziawg", "udp") == ("sing-box-lx",)


def test_ssh_is_supported_by_singbox():
    assert "sing-box-lx" in preferred_cores("ssh", "tcp")
