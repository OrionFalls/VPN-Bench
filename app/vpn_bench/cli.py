import argparse

from .config import load_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="VPN-Bench")
    parser.add_argument(
        "--config",
        default="/app/config/config.example.yaml",
        help="Path to YAML configuration",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_config(args.config)
    print(
        f"VPN-Bench {config.app.version} ready "
        f"with {len(config.providers)} configured provider(s)."
    )
