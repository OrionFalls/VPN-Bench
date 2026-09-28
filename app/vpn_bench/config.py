from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AppConfig:
    host: str
    port: int
    database: str
    version: str = "0.2.0"


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    subscription_url: str
    enabled: bool


@dataclass(frozen=True)
class BenchmarkConfig:
    update_interval_seconds: int = 1
    default_duration_seconds: int = 600
    default_mode: str = "equal_time"
    retention_days: int = 90


@dataclass(frozen=True)
class Config:
    app: AppConfig
    providers: tuple[ProviderConfig, ...]
    benchmark: BenchmarkConfig


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

    benchmark_data = data.get("benchmark", {})
    benchmark = BenchmarkConfig(
        update_interval_seconds=max(1, int(benchmark_data.get("update_interval_seconds", 1))),
        default_duration_seconds=max(1, int(benchmark_data.get("default_duration_seconds", 600))),
        default_mode=str(benchmark_data.get("default_mode", "equal_time")),
        retention_days=max(1, int(benchmark_data.get("retention_days", 90))),
    )

    return Config(app=app, providers=providers, benchmark=benchmark)
