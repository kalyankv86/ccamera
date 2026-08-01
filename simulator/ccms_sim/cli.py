"""ccms-sim run           - launch the simulator's control/ONVIF API + all camera feeds
ccms-sim down <sim_id>    - force a device down (scope=stream by default)
ccms-sim up <sim_id>      - recover a device
ccms-sim list             - list simulated devices and their current state
"""

import httpx
import typer
import uvicorn

app = typer.Typer(help="CCMS device simulator control CLI")

DEFAULT_CONTROL_URL = "http://127.0.0.1:9500"


@app.command()
def run(host: str = "127.0.0.1", port: int = 9500, count: int = 8) -> None:
    """Starts the control/ONVIF API (and, via its lifespan, every camera's
    ffmpeg feed). `count` only affects scripts/seed_simulated_devices.py's
    manifest expectations if changed - the manifest itself is fixed at import
    time in manifest.py's default, so keep this in sync if you change it."""
    uvicorn.run("ccms_sim.control_api:app", host=host, port=port, log_level="info")


@app.command()
def down(sim_id: str, scope: str = "stream", control_url: str = DEFAULT_CONTROL_URL) -> None:
    resp = httpx.post(f"{control_url}/sim/devices/{sim_id}/fail", params={"scope": scope}, timeout=10)
    resp.raise_for_status()
    typer.echo(resp.json())


@app.command()
def up(sim_id: str, control_url: str = DEFAULT_CONTROL_URL) -> None:
    resp = httpx.post(f"{control_url}/sim/devices/{sim_id}/recover", timeout=10)
    resp.raise_for_status()
    typer.echo(resp.json())


@app.command(name="list")
def list_devices(control_url: str = DEFAULT_CONTROL_URL) -> None:
    resp = httpx.get(f"{control_url}/sim/devices", timeout=10)
    resp.raise_for_status()
    typer.echo(resp.json())


if __name__ == "__main__":
    app()
