from vpn_bench.security import hash_password, verify_password


def test_password_hash_roundtrip():
    encoded = hash_password("a-strong-test-password")
    assert encoded != "a-strong-test-password"
    assert verify_password("a-strong-test-password", encoded)
    assert not verify_password("wrong-password", encoded)
