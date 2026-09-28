from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os

from .config import load_config
from .db import initialize


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/health":
            body = b'{"status":"ok"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        body = b"VPN-Bench is running\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    config_path = os.environ.get(
        "VPN_BENCH_CONFIG", "/app/config/config.example.yaml"
    )
    config = load_config(config_path)
    initialize(config.app.database)

    server = ThreadingHTTPServer((config.app.host, config.app.port), Handler)
    print(f"VPN-Bench listening on {config.app.host}:{config.app.port}", flush=True)
    server.serve_forever()
