from vpn_bench.db import initialize


def test_initialize_database(tmp_path):
    database = tmp_path / "vpn-bench.sqlite3"

    initialize(database)

    assert database.exists()
