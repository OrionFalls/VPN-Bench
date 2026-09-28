"""Planning primitives for two-pass VPN screening campaigns."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScreeningPlan:
    """Short, repeatable screening schedule.

    Pass one is deliberately cheap. Pass two rechecks only survivors so a
    transient network failure does not discard a usable server.
    """

    first_pass_seconds: int = 30
    second_pass_seconds: int = 30
    repeat_passes: int = 2
    max_shortlist: int | None = None

    def __post_init__(self) -> None:
        if self.first_pass_seconds <= 0 or self.second_pass_seconds <= 0:
            raise ValueError("Screening pass duration must be greater than zero.")
        if self.repeat_passes < 1:
            raise ValueError("Screening must contain at least one pass.")
        if self.max_shortlist is not None and self.max_shortlist <= 0:
            raise ValueError("max_shortlist must be positive when set.")

    @property
    def first_pass_duration(self) -> int:
        return self.first_pass_seconds

    @property
    def repeat_pass_duration(self) -> int:
        return self.second_pass_seconds

    def next_candidates(
        self,
        server_ids: list[str],
        survivors: list[str] | None = None,
    ) -> list[str]:
        """Return the servers that should enter the next pass."""

        candidates = list(server_ids if survivors is None else survivors)
        if self.max_shortlist is not None:
            candidates = candidates[: self.max_shortlist]
        return candidates
