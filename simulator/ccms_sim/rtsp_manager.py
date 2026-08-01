"""Each simulated camera is one `ffmpeg` subprocess pushing a synthetic test
pattern into mediamtx's RTSP server. Killing that subprocess is exactly how
"stream DOWN" is simulated while the camera's fake ONVIF/ping endpoints stay
healthy - RtspChecker sees a real connection-refused/no-frames failure."""

import subprocess

RTSP_BASE = "rtsp://127.0.0.1:8554"


class RtspManager:
    def __init__(self) -> None:
        self._procs: dict[str, subprocess.Popen] = {}

    def start(self, sim_id: str) -> None:
        if self.is_running(sim_id):
            return
        cmd = [
            "ffmpeg", "-re",
            "-f", "lavfi", "-i", "testsrc=size=640x480:rate=15",
            "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
            "-f", "rtsp", f"{RTSP_BASE}/{sim_id}",
        ]
        self._procs[sim_id] = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def stop(self, sim_id: str) -> None:
        proc = self._procs.pop(sim_id, None)
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    def is_running(self, sim_id: str) -> bool:
        proc = self._procs.get(sim_id)
        return proc is not None and proc.poll() is None

    def stop_all(self) -> None:
        for sim_id in list(self._procs):
            self.stop(sim_id)


manager = RtspManager()
