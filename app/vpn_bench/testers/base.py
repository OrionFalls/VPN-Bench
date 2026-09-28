from abc import ABC, abstractmethod

from ..models import Server, TestResult


class BenchmarkTester(ABC):
    @abstractmethod
    def run(self, server: Server) -> TestResult:
        """Run the configured benchmark against one connected server."""

    @abstractmethod
    def capabilities(self) -> set[str]:
        """Return supported benchmark names."""
