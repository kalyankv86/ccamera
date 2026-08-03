"""Manages per-camera live-view paths in mediamtx (an on-demand RTSP-to-HLS
relay) via its local REST API. mediamtx only connects to a camera's RTSP
stream when a viewer actually requests the HLS playlist (sourceOnDemand),
so registering all cameras doesn't mean continuously pulling every stream -
only the ones someone is actively watching.

Distinct from the dev simulator's use of mediamtx (simulator/ccms_sim/
rtsp_manager.py), which *publishes* synthetic streams into mediamtx under
different path names (camNNN) - this module instead tells mediamtx to *pull
from* a real camera's RTSP URL on demand. Both usages coexist fine in one
mediamtx instance; path names are namespaced (live_<device_id> here) so
there's no collision.
"""

import httpx

from ccms.config import settings

_API_TIMEOUT = 5.0


def _path_name(device_id: int) -> str:
    return f"live_{device_id}"


def register_path(device_id: int, authenticated_rtsp_url: str) -> None:
    """Idempotent: PATCHes the path into existence if missing, else updates
    its source (e.g. after a credential/rtsp_url change)."""
    name = _path_name(device_id)
    body = {"source": authenticated_rtsp_url, "sourceOnDemand": True}
    base = settings.mediamtx_api_url
    try:
        resp = httpx.post(f"{base}/v3/config/paths/add/{name}", json=body, timeout=_API_TIMEOUT)
        if resp.status_code == 400:
            # already exists - update it instead (e.g. credentials changed)
            resp = httpx.patch(f"{base}/v3/config/paths/patch/{name}", json=body, timeout=_API_TIMEOUT)
        resp.raise_for_status()
    except httpx.HTTPError:
        pass  # live view is a convenience feature - never block device CRUD on mediamtx being reachable


def remove_path(device_id: int) -> None:
    name = _path_name(device_id)
    try:
        httpx.delete(f"{settings.mediamtx_api_url}/v3/config/paths/delete/{name}", timeout=_API_TIMEOUT)
    except httpx.HTTPError:
        pass


def hls_url_for(device_id: int) -> str:
    """Relative URL, proxied through the same Nginx origin as everything
    else (deploy/nginx/ccms.conf.template) - avoids exposing mediamtx's HLS
    port directly or dealing with a second origin/CORS in the frontend."""
    return f"{settings.mediamtx_hls_public_base}/{_path_name(device_id)}/index.m3u8"
