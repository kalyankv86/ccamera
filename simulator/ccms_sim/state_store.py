"""In-memory state shared between rtsp_manager, onvif_fake, and control_api
within a single simulator process. Not persisted - restarting the simulator
resets everything back to healthy, which is fine for a dev/demo tool."""

from dataclasses import dataclass, field


@dataclass
class CameraState:
    stream_failed: bool = False


@dataclass
class NvrState:
    failed: bool = False
    recording: bool = True
    hdd_status: str = "ok"
    disk_pct: float = 45.0
    clock_drift_s: float = 1.5


class StateStore:
    def __init__(self) -> None:
        self.cameras: dict[str, CameraState] = {}
        self.nvrs: dict[str, NvrState] = {}

    def camera(self, sim_id: str) -> CameraState:
        return self.cameras.setdefault(sim_id, CameraState())

    def nvr(self, sim_id: str) -> NvrState:
        return self.nvrs.setdefault(sim_id, NvrState())


store = StateStore()
