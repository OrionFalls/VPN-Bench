from vpn_bench.config import load_config


def test_load_config(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
app:
  host: 127.0.0.1
  port: 9000
  database: /tmp/test.sqlite3
providers:
  - name: test
    subscription_url: https://example.test/sub
    enabled: true
""",
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.app.host == "127.0.0.1"
    assert config.app.port == 9000
    assert config.providers[0].name == "test"
    assert config.providers[0].enabled is True
