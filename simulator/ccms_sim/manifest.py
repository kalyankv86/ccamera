"""Defines the fixed set of simulated cameras/NVRs. Both the simulator
processes (rtsp_manager, onvif_fake, control_api) and
scripts/seed_simulated_devices.py read this same manifest, so the CCMS device
registry and the simulator's own state always agree on what exists.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SimNvr:
    sim_id: str
    name: str
    building: str
    zone: str


@dataclass(frozen=True)
class SimCamera:
    sim_id: str
    name: str
    nvr_sim_id: str
    channel_no: int
    building: str
    zone: str
    criticality: str = "normal"


def build_manifest(camera_count: int = 8, cameras_per_nvr: int = 4) -> tuple[list[SimNvr], list[SimCamera]]:
    nvr_count = max(1, -(-camera_count // cameras_per_nvr))  # ceil division
    nvrs = [
        SimNvr(sim_id=f"nvr{i + 1:03d}", name=f"Simulated NVR {i + 1}", building="Simulator Block", zone=f"Rack {i + 1}")
        for i in range(nvr_count)
    ]

    cameras = []
    for i in range(camera_count):
        nvr = nvrs[i // cameras_per_nvr]
        channel_no = (i % cameras_per_nvr) + 1
        cameras.append(
            SimCamera(
                sim_id=f"cam{i + 1:03d}",
                name=f"Simulated Camera {i + 1}",
                nvr_sim_id=nvr.sim_id,
                channel_no=channel_no,
                building="Simulator Block",
                zone=f"Zone {(i // 2) + 1}",
                criticality="critical" if i == 0 else "normal",
            )
        )
    return nvrs, cameras
