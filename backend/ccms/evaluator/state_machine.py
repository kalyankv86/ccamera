"""FR-06: combines check results into a single device state with debouncing so
transient blips don't raise alerts. State transition requires N consecutive
confirming checks (default 3 down / 2 up, configurable)."""

from dataclasses import dataclass

from ccms.config import settings
from ccms.models.enums import CheckStatus, DeviceState

# A DOWN-capable check failing means the device itself might be down; DEGRADED
# never forces DOWN on its own (FR-06: DOWN requires network/stream hard failure).
_HARD_FAIL_STATUSES = {CheckStatus.FAIL, CheckStatus.ERROR}


@dataclass
class DebounceCounters:
    consecutive_fail: int = 0
    consecutive_ok: int = 0


def next_state(
    current_state: DeviceState,
    counters: DebounceCounters,
    check_status: CheckStatus,
    *,
    down_threshold: int | None = None,
    up_threshold: int | None = None,
) -> tuple[DeviceState, DebounceCounters]:
    down_threshold = down_threshold or settings.debounce_down_count
    up_threshold = up_threshold or settings.debounce_up_count

    if current_state == DeviceState.MAINTENANCE:
        return current_state, counters

    if check_status in _HARD_FAIL_STATUSES:
        counters.consecutive_fail += 1
        counters.consecutive_ok = 0
        if counters.consecutive_fail >= down_threshold:
            return DeviceState.DOWN, counters
        return current_state, counters

    if check_status == CheckStatus.DEGRADED:
        counters.consecutive_fail = 0
        counters.consecutive_ok = 0
        if current_state == DeviceState.DOWN:
            return current_state, counters  # still needs consecutive OKs to recover
        return DeviceState.DEGRADED, counters

    # OK
    counters.consecutive_ok += 1
    counters.consecutive_fail = 0
    if current_state == DeviceState.DOWN and counters.consecutive_ok < up_threshold:
        return current_state, counters
    return DeviceState.UP, counters
