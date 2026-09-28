from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AppConfig:
    host: str
    port: int
    database: str
    version: str = "0.1.0"


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    subscription_url: str
    enabled: bool


@dataclass(frozen=True)
class Config:
    app: AppConfig
    providers: tuple[ProviderConfig, ...]


def load_config(path: str | Path) -> Config:
    data: dict[str, Any] = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}

    app_data = data.get("app", {})
    app = AppConfig(
        host=str(app_data.get("host", "0.0.0.0")),
        port=int(app_data.get("port", 8080)),
        database=str(app_data.get("database", "./data/vpn-bench.sqlite3")),
    )

    providers = tuple(
        ProviderConfig(
            name=str(item["name"]),
            subscription_url=str(item["subscription_url"]),
            enabled=bool(item.get("enabled", True)),
        )
        for item in data.get("providers", [])
    )

    return Config(app=app, providers=providers)
