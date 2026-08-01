"""Registers the simulator's manifest (simulator/ccms_sim/manifest.py) as
ordinary devices/NVR rows in the CCMS registry - they're just devices whose
ip/rtsp_url/onvif_url point at localhost, so checkers/evaluator/alerts/
dashboard have zero special-case code for "simulated" vs real. Idempotent:
safe to re-run (matches by name)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "simulator"))

from ccms_sim.manifest import build_manifest  # noqa: E402

from ccms.db import SessionLocal  # noqa: E402
from ccms.models.device import Device  # noqa: E402
from ccms.models.enums import Criticality, DeviceType  # noqa: E402

RTSP_BASE = "rtsp://127.0.0.1:8554"
SIM_CONTROL_URL = "http://127.0.0.1:9500"


def main() -> None:
    nvrs, cameras = build_manifest()
    db = SessionLocal()
    try:
        nvr_id_by_sim: dict[str, int] = {}

        for nvr in nvrs:
            row = db.query(Device).filter(Device.name == nvr.name).first()
            if row is None:
                row = Device(type=DeviceType.NVR, name=nvr.name, ip="127.0.0.1")
                db.add(row)
                db.flush()
            row.onvif_url = f"{SIM_CONTROL_URL}/sim/nvr/{nvr.sim_id}/status"
            row.building = nvr.building
            row.zone = nvr.zone
            row.criticality = Criticality.HIGH
            row.active = True
            nvr_id_by_sim[nvr.sim_id] = row.id

        db.flush()

        for camera in cameras:
            row = db.query(Device).filter(Device.name == camera.name).first()
            if row is None:
                row = Device(type=DeviceType.CAMERA, name=camera.name, ip="127.0.0.1")
                db.add(row)
                db.flush()
            row.rtsp_url = f"{RTSP_BASE}/{camera.sim_id}"
            row.parent_nvr_id = nvr_id_by_sim[camera.nvr_sim_id]
            row.channel_no = camera.channel_no
            row.building = camera.building
            row.zone = camera.zone
            row.criticality = Criticality(camera.criticality)
            row.active = True

        db.commit()
        print(f"Seeded {len(nvrs)} simulated NVRs and {len(cameras)} simulated cameras.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
