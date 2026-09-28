import pytest

from vpn_bench.subscription import SubscriptionError, _validate_subscription_url


def test_subscription_rejects_loopback():
    with pytest.raises(SubscriptionError):
        _validate_subscription_url("http://127.0.0.1:8080/subscription")


def test_subscription_rejects_non_http():
    with pytest.raises(SubscriptionError):
        _validate_subscription_url("file:///etc/passwd")
