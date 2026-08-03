import { useEffect, useRef, useState } from "react";
import Hls from "hls.js";
import { api, ApiError } from "../api/client";

/** On-demand HLS live view (see backend ccms.live.mediamtx_client). Starts
 * disconnected - mediamtx only pulls the camera's RTSP stream once someone
 * actually clicks "Watch live", not just because the device page is open. */
export function LivePlayer({ deviceId }: { deviceId: number }) {
  const [watching, setWatching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const hlsRef = useRef<Hls | null>(null);

  useEffect(() => {
    if (!watching) return;
    let cancelled = false;

    api
      .get<{ hls_url: string }>(`/devices/${deviceId}/live`)
      .then(({ hls_url }) => {
        if (cancelled) return;
        const video = videoRef.current;
        if (!video) return;

        const fullUrl = `${hls_url}?_=${Date.now()}`; // avoid a stale cached playlist on reconnect

        if (Hls.isSupported()) {
          const hls = new Hls({ maxLiveSyncPlaybackRate: 1.5 });
          hlsRef.current = hls;
          hls.on(Hls.Events.ERROR, (_evt, data) => {
            if (data.fatal) setError("Stream error - the camera may be offline or still starting up.");
          });
          hls.loadSource(fullUrl);
          hls.attachMedia(video);
          video.play().catch(() => {});
        } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
          video.src = fullUrl; // Safari has native HLS support
          video.play().catch(() => {});
        } else {
          setError("This browser doesn't support HLS playback.");
        }
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to start live view"));

    return () => {
      cancelled = true;
      hlsRef.current?.destroy();
      hlsRef.current = null;
    };
  }, [watching, deviceId]);

  if (!watching) {
    return (
      <button className="ack-btn" onClick={() => { setError(null); setWatching(true); }}>
        Watch live
      </button>
    );
  }

  return (
    <div>
      {error ? (
        <p className="error-text">{error}</p>
      ) : (
        <video
          ref={videoRef}
          controls
          muted
          playsInline
          style={{ width: "100%", maxWidth: 480, borderRadius: 4, border: "1px solid var(--border)", background: "#000" }}
        />
      )}
      <div>
        <button className="ack-btn" style={{ marginTop: 8 }} onClick={() => setWatching(false)}>
          Stop watching
        </button>
      </div>
    </div>
  );
}
