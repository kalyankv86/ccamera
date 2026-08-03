"""One-off backfill: registers mediamtx live-view paths for every active
camera that already existed before the live-view feature was added. New
cameras get this automatically via the API (ccms.api.routers.devices), so
this only needs to run once against an existing fleet."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from ccms.api.routers.devices import _sync_live_view  # noqa: E402
from ccms.db import SessionLocal  # noqa: E402
from ccms.models.device import Device  # noqa: E402
from ccms.models.enums import DeviceType  # noqa: E402


def main() -> None:
    db = SessionLocal()
    try:
        cameras = db.query(Device).filter(Device.type == DeviceType.CAMERA, Device.active.is_(True)).all()
        for device in cameras:
            _sync_live_view(device)
        print(f"Synced live-view paths for {len(cameras)} cameras")
    finally:
        db.close()


if __name__ == "__main__":
    main()
