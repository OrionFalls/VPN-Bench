from vpn_bench.network_namespace import NamespaceManager


def test_namespace_manager_allocates_routed_30(monkeypatch):
    manager = NamespaceManager("10.250.0.0/16")
    calls = []

    monkeypatch.setattr(manager, "_require_commands", lambda: None)
    monkeypatch.setattr(manager, "_default_interface", lambda: "eth0")

    def fake_run(args, check=True):
        calls.append(args)
        class Result:
            returncode = 0
            stdout = ""
            stderr = ""
        return Result()

    monkeypatch.setattr(manager, "_run", fake_run)

    ns = manager.create("abcdef123456")
    assert ns.subnet == "10.250.0.0/30"
    assert ns.host_ip == "10.250.0.1"
    assert ns.namespace_ip == "10.250.0.2"
    assert ["ip", "netns", "add", ns.name] in calls
    assert ["iptables", "-t", "nat", "-A", "POSTROUTING", "-s", ns.subnet, "-o", "eth0", "-j", "MASQUERADE"] in calls

    manager.destroy(ns)


def test_nat_uses_pinned_uplink(monkeypatch):
    manager = NamespaceManager()
    commands = []

    monkeypatch.setattr(manager, "_run", lambda args, check=True: commands.append(args))

    ns = type("NS", (), {
        "subnet": "10.250.4.0/30",
        "uplink": "eth9",
    })()

    manager._add_nat(ns)
    manager._delete_nat(ns)

    assert commands[0][7:9] == ["-o", "eth9"]
    assert commands[1][7:9] == ["-o", "eth9"]
