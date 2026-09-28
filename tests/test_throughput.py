from vpn_bench.throughput import download_sample


def test_download_sample_uses_proxy(monkeypatch):
    seen = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, size):
            seen["size"] = size
            return b"x" * min(size, 1024)

    class Opener:
        def open(self, request, timeout):
            seen["url"] = request.full_url
            return Response()

    monkeypatch.setattr(
        "vpn_bench.throughput.urllib.request.build_opener",
        lambda handler: Opener(),
    )
    result = download_sample(
        "https://bench.example/1m.bin",
        "http://127.0.0.1:1234",
        duration_seconds=0.01,
    )
    assert result["ok"]
    assert seen["url"] == "https://bench.example/1m.bin"
