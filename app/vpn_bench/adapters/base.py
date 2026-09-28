from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Iterator


@dataclass(frozen=True)
class ConnectionHandle:
    server_id: str
    metadata: dict[str, Any]


class VPNAdapter(ABC):
    @abstractmethod
    def import_servers(self, source: str) -> Iterator[dict[str, Any]]:
        """Convert a provider source into normalized server definitions."""

    @abstractmethod
    def connect(self, server: dict[str, Any]) -> ConnectionHandle:
        """Create an isolated VPN connection for a single server."""

    @abstractmethod
    def disconnect(self, handle: ConnectionHandle) -> None:
        """Tear down the VPN connection."""
