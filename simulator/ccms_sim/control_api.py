"""Single FastAPI app serving two roles:

1. Fake NVR/ONVIF endpoint (/sim/nvr/{sim_id}/status) - returns the same
   normalized JSON shape ccms.checkers.nvr.NvrChecker expects from a real
   vendor adapter, so it's a first-class "vendor" the checker already knows
   how to talk to (see NvrChecker._query's simulator branch).

2. Control surface (/sim/devices, /sim/devices/{sim_id}/fail|recover) used by
   ccms_sim/cli.py and by hand during demos to force a device down/up on
   command, so the checker -> evaluator -> alert -> notification -> dashboard
   pipeline can be exercised without physical hardware.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from ccms_sim.manifest import build_manifest
from ccms_sim.rtsp_manager import manager as rtsp_manager
from ccms_sim.state_store import store

_nvrs, _cameras = build_manifest()
_nvr_by_id = {n.sim_id: n for n in _nvrs}
_camera_by_id = {c.sim_id: c for c in _cameras}


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    for camera in _cameras:
        rtsp_manager.start(camera.sim_id)
    yield
    rtsp_manager.stop_all()


app = FastAPI(title="CCMS Device Simulator", lifespan=_lifespan)


@app.get("/sim/devices")
def list_devices() -> dict:
    return {
        "cameras": [
            {
                "sim_id": c.sim_id, "name": c.name, "nvr_sim_id": c.nvr_sim_id,
                "stream_failed": store.camera(c.sim_id).stream_failed,
                "stream_running": rtsp_manager.is_running(c.sim_id),
            }
            for c in _cameras
        ],
        "nvrs": [
            {"sim_id": n.sim_id, "name": n.name, **vars(store.nvr(n.sim_id))}
            for n in _nvrs
        ],
    }


@app.get("/sim/nvr/{sim_id}/status")
def nvr_status(sim_id: str) -> dict:
    """Normalized shape consumed directly by NvrChecker (no ONVIF/SOAP needed
    for the simulator vendor branch)."""
    if sim_id not in _nvr_by_id:
        raise HTTPException(404, detail="unknown simulated NVR")
    state = store.nvr(sim_id)
    if state.failed:
        raise HTTPException(503, detail="simulated NVR failure")
    return {
        "recording": state.recording,
        "hdd_status": state.hdd_status,
        "disk_pct": state.disk_pct,
        "clock_drift_s": state.clock_drift_s,
    }


@app.post("/sim/devices/{sim_id}/fail")
def fail_device(sim_id: str, scope: str = "stream") -> dict:
    """scope=stream: kills the camera's ffmpeg feed (RTSP/image checks fail).
    scope=nvr: makes the camera's parent NVR's fake status endpoint fail
    (NVR checks fail for that NVR, and by extension its channels).
    scope=network: no true ICMP-down on localhost without sudo/pf tricks
    (documented limitation) - treated as stream+nvr both down, which is what
    a genuinely dead camera looks like to the checkers anyway."""
    if sim_id in _camera_by_id:
        camera = _camera_by_id[sim_id]
        if scope in ("stream", "network"):
            store.camera(sim_id).stream_failed = True
            rtsp_manager.stop(sim_id)
        if scope in ("nvr", "network"):
            store.nvr(camera.nvr_sim_id).failed = True
        if scope not in ("stream", "nvr", "network"):
            raise HTTPException(400, detail="scope must be stream, nvr, or network")
        return {"sim_id": sim_id, "scope": scope, "status": "failed"}

    if sim_id in _nvr_by_id:
        store.nvr(sim_id).failed = True
        return {"sim_id": sim_id, "scope": "nvr", "status": "failed"}

    raise HTTPException(404, detail="unknown simulated device")


@app.post("/sim/devices/{sim_id}/recover")
def recover_device(sim_id: str) -> dict:
    if sim_id in _camera_by_id:
        camera = _camera_by_id[sim_id]
        store.camera(sim_id).stream_failed = False
        rtsp_manager.start(sim_id)
        store.nvr(camera.nvr_sim_id).failed = False
        return {"sim_id": sim_id, "status": "recovered"}

    if sim_id in _nvr_by_id:
        store.nvr(sim_id).failed = False
        return {"sim_id": sim_id, "status": "recovered"}

    raise HTTPException(404, detail="unknown simulated device")


@app.post("/sim/nvr/{sim_id}/set")
def set_nvr_metrics(
    sim_id: str,
    recording: bool | None = None,
    hdd_status: str | None = None,
    disk_pct: float | None = None,
    clock_drift_s: float | None = None,
) -> dict:
    """Lets a demo drive DISK_USAGE_HIGH / HDD_FAILURE / CLOCK_DRIFT warnings
    (FR-05) without a full fail/recover cycle."""
    if sim_id not in _nvr_by_id:
        raise HTTPException(404, detail="unknown simulated NVR")
    state = store.nvr(sim_id)
    if recording is not None:
        state.recording = recording
    if hdd_status is not None:
        state.hdd_status = hdd_status
    if disk_pct is not None:
        state.disk_pct = disk_pct
    if clock_drift_s is not None:
        state.clock_drift_s = clock_drift_s
    return vars(state)
