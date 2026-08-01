from abc import ABC, abstractmethod
from typing import ClassVar, Literal, NamedTuple


class DeliveryResult(NamedTuple):
    status: Literal["SENT", "FAILED", "SKIPPED_NOT_CONFIGURED"]
    detail: str | None = None


class NotificationAdapter(ABC):
    channel: ClassVar[str]

    @abstractmethod
    def is_configured(self) -> bool: ...

    @abstractmethod
    def send(self, *, message: str, recipient: str, subject: str | None = None) -> DeliveryResult: ...
