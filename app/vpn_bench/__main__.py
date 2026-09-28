import os

import uvicorn

from .api import build_app
from .config import load_config


def main() -> None:
    config_path = os.environ.get("VPN_BENCH_CONFIG", "/app/config/config.yaml")
    config = load_config(config_path)
    app = build_app(config)
    uvicorn.run(
        app,
        host=config.app.host,
        port=config.app.port,
    )


if __name__ == "__main__":
    main()
