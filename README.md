# CCMS - Campus Camera & NVR Health Monitoring System

Monitors campus IP cameras and NVRs for health (network/stream/image/recording),
raises alerts (email live in dev via Mailpit; SMS/WhatsApp wired but inactive
until credentials are supplied), and provides a web dashboard and SLA reporting.

Built from `CCMS_SRS.docx` / `CCMS_SDD.docx` in this directory. See
`/Users/kalyan/.claude/plans/hazy-wishing-orbit.md` for the full implementation
plan, milestones and deviations from the SDD (plain PostgreSQL instead of
TimescaleDB, no Docker, a device simulator standing in for physical hardware).

## Quick start (macOS, Homebrew)

```
./scripts/dev_bootstrap.sh   # one-time: installs deps, creates DB, migrates, seeds admin
./scripts/start_all.sh       # one command: API + Celery + frontend + Mailpit + simulator
```

- API: http://localhost:8000 (docs at `/api/docs`)
- Dashboard: http://localhost:5173
- Mailpit (dev email catcher): http://localhost:8025
- Default admin login: `admin@ccms.campus` / `ChangeMe123!` (change immediately)

After bootstrap, register the simulator's demo fleet (2 NVRs + 8 cameras):
`backend/.venv/bin/python scripts/seed_simulated_devices.py`

## Production deployment (Ubuntu Server)

```
git clone https://github.com/kalyankv86/ccamera.git && cd ccamera
./scripts/deploy_ubuntu.sh
```

Provisions Postgres/Redis/Nginx/msmtp, creates a dedicated `ccms` system
user, builds the frontend, installs systemd units for the API + beat + 3
Celery worker queues (auto-restart on crash - unlike the dev-mode `honcho`
setup), and sets up Nginx with a real TLS cert via certbot. Does **not**
install mediamtx/the simulator - production points at real camera/NVR IPs.
Safe to re-run for redeploying updated code; it will not regenerate secrets
or touch an existing `.env`. See `deploy/` for the systemd units, Nginx
template, and `deploy/msmtprc.template` (fill in your real mail relay after
the script runs, then `sudo systemctl status ccms-api ccms-beat
ccms-worker-net ccms-worker-stream ccms-worker-misc` to confirm everything's
up). This script has not been run against a real Ubuntu box in this repo's
own development - review it before running against a production system.

## Layout

- `backend/` - FastAPI + Celery/Redis + PostgreSQL (SQLAlchemy/Alembic)
- `frontend/` - React/Vite dashboard
- `simulator/` - fake cameras/NVRs for demoing the pipeline without hardware
- `scripts/` - bootstrap, process startup, admin/device seeding, partition management

## Status

All Phase-1 SRS functional requirements (FR-01 through FR-16) are implemented
and, with one exception, verified live against the simulator through the
actual `start_all.sh` orchestration: device registry/CSV import, JWT auth +
RBAC + audit log, ping/RTSP/NVR/image checkers, debounce state machine,
storm-grouped alerting with tiered escalation (FR-08), email notifications
(SMS/WhatsApp adapters wired, dormant until real credentials are configured),
the web dashboard (live map, device detail, alerts, reports, admin), FR-12
maintenance-window suppression, FR-11 flapping detection + disk-full
forecasting, and FR-10 uptime/SLA reports (JSON/PDF/Excel + a real scheduled
monthly email).

**Known gaps:**
- **FR-15 SNMP/PoE monitoring** (explicitly lowest-priority / "may be
  deferred" in the SRS): `SnmpChecker` is implemented and confirmed to fail
  gracefully against a nonexistent agent, but no SNMP agent was built into the
  simulator, so it's unverified against a real responder. `Device.channel_no`
  currently means "NVR recording channel" (FR-01); a real switch-port mapping
  for PoE root-cause grouping would need a separate field.
- **Auto-restart on crash**: `honcho` (the no-Docker dev process runner) does
  not restart a crashed process - fine for local dev, not for production.
  `scripts/deploy_ubuntu.sh` addresses this for real deployments with
  systemd units (`Restart=on-failure`) instead of honcho.
- **True network-level (ICMP) DOWN** can't be simulated against `127.0.0.1`
  without `sudo pf` tricks; the simulator's `scope=network` fail mode is
  stream+nvr-down instead, which is what a genuinely dead camera looks like
  to the checkers anyway.
