from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ccms.models.enums import CheckStatus, CheckType
from ccms.models.device import Device


@dataclass
class CheckResultData:
    """In-memory result of a single checker run; persisted to check_results by the
    Celery task wrapper (checkers/tasks.py), not by the checker itself, so checkers
    stay pure and unit-testable."""

    check_type: CheckType
    status: CheckStatus
    latency_ms: float | None = None
    loss_pct: float | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class BaseChecker(ABC):
    check_type: CheckType
    timeout_s: float = 10.0

    @abstractmethod
    def run(self, device: Device) -> CheckResultData:
        """Never raises: any unhandled error must be caught by the Celery task
        wrapper and converted into CheckResultData(status=ERROR, error=...) so a
        hung/broken device can't crash a worker (SDD 6.4)."""
        raise NotImplementedError
