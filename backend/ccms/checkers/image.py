"""FR-04 / SDD 3.2.3: grabs one frame and analyses it for black/blank, frozen,
blurred, and scene-change (tamper) conditions."""

import hashlib
from pathlib import Path

import cv2
import numpy as np

from ccms.checkers.base import BaseChecker, CheckResultData
from ccms.checkers.credentials import build_authenticated_rtsp_url
from ccms.models.device import Device
from ccms.models.enums import CheckStatus, CheckType

BLACK_LUMINANCE_THRESHOLD = 10.0
BLUR_LAPLACIAN_THRESHOLD = 50.0
SCENE_CHANGE_SSIM_THRESHOLD = 0.5
_SNAPSHOT_DIR = Path(__file__).resolve().parents[3] / "data" / "snapshots"


class ImageChecker(BaseChecker):
    check_type = CheckType.IMAGE
    timeout_s = 10.0

    def run(self, device: Device) -> CheckResultData:
        if not device.rtsp_url:
            return CheckResultData(check_type=self.check_type, status=CheckStatus.ERROR, error="no rtsp_url configured")

        url = build_authenticated_rtsp_url(device.id, device.rtsp_url)
        frame = self._grab_frame(url)
        if frame is None:
            return CheckResultData(check_type=self.check_type, status=CheckStatus.FAIL, error="capture failed")

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_luminance = float(gray.mean())
        laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        frame_hash = hashlib.sha256(gray.tobytes()).hexdigest()

        _SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        latest_path = _SNAPSHOT_DIR / f"device_{device.id}_latest.jpg"
        reference_path = _SNAPSHOT_DIR / f"device_{device.id}_reference.jpg"
        prev_hash_path = _SNAPSHOT_DIR / f"device_{device.id}_prev.hash"

        frozen = False
        if prev_hash_path.exists() and prev_hash_path.read_text().strip() == frame_hash:
            frozen = True
        prev_hash_path.write_text(frame_hash)

        scene_changed = False
        if reference_path.exists():
            reference = cv2.imread(str(reference_path), cv2.IMREAD_GRAYSCALE)
            if reference is not None and reference.shape == gray.shape:
                scene_changed = self._ssim(gray, reference) < SCENE_CHANGE_SSIM_THRESHOLD
        else:
            cv2.imwrite(str(reference_path), gray)  # first run sets the reference

        cv2.imwrite(str(latest_path), frame)

        metrics = {
            "mean_luminance": mean_luminance,
            "laplacian_var": laplacian_var,
            "frozen": frozen,
            "scene_changed": scene_changed,
        }

        if mean_luminance < BLACK_LUMINANCE_THRESHOLD:
            return CheckResultData(check_type=self.check_type, status=CheckStatus.FAIL, error="BLACK_IMAGE", metrics=metrics)
        if frozen:
            return CheckResultData(check_type=self.check_type, status=CheckStatus.FAIL, error="FROZEN_IMAGE", metrics=metrics)
        if laplacian_var < BLUR_LAPLACIAN_THRESHOLD:
            return CheckResultData(check_type=self.check_type, status=CheckStatus.DEGRADED, error="BLURRED", metrics=metrics)
        if scene_changed:
            return CheckResultData(check_type=self.check_type, status=CheckStatus.DEGRADED, error="SCENE_CHANGE", metrics=metrics)

        return CheckResultData(check_type=self.check_type, status=CheckStatus.OK, metrics=metrics)

    def _grab_frame(self, rtsp_url: str) -> np.ndarray | None:
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        try:
            if not cap.isOpened():
                return None
            ok, frame = cap.read()
            return frame if ok else None
        finally:
            cap.release()

    @staticmethod
    def _ssim(a: np.ndarray, b: np.ndarray) -> float:
        """Lightweight single-scale SSIM (avoids a scikit-image dependency)."""
        a = a.astype(np.float64)
        b = b.astype(np.float64)
        c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
        mu_a, mu_b = a.mean(), b.mean()
        var_a, var_b = a.var(), b.var()
        cov_ab = ((a - mu_a) * (b - mu_b)).mean()
        return float(
            ((2 * mu_a * mu_b + c1) * (2 * cov_ab + c2))
            / ((mu_a**2 + mu_b**2 + c1) * (var_a + var_b + c2))
        )
