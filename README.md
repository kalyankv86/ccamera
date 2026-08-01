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

## Layout

- `backend/` - FastAPI + Celery/Redis + PostgreSQL (SQLAlchemy/Alembic)
- `frontend/` - React/Vite dashboard
- `simulator/` - fake cameras/NVRs for demoing the pipeline without hardware
- `scripts/` - bootstrap, process startup, admin/device seeding, partition management
