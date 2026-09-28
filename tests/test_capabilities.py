from vpn_bench.capabilities import preferred_cores


def test_preferred_cores_deduplicates_amneziawg():
    assert preferred_cores("amneziawg", "udp") == ("sing-box-lx",)


def test_ssh_is_supported_by_singbox():
    assert "sing-box-lx" in preferred_cores("ssh", "tcp")


def test_xray_capability_requires_installed_binary(monkeypatch):
    import vpn_bench.capabilities as capabilities

    monkeypatch.setattr(capabilities.shutil, "which", lambda _: None)
    items = capabilities.detect_capabilities("vless", "xhttp")
    xray = next(item for item in items if item.core == "xray")
    assert xray.supported is False
    assert "not installed" in xray.reason
