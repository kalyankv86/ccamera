api:           bash -c 'cd backend && .venv/bin/uvicorn ccms.main:app --host 0.0.0.0 --port 8000 --reload'
beat:          bash -c 'cd backend && .venv/bin/celery -A ccms.celery_app beat -l info'
worker_net:    bash -c 'cd backend && .venv/bin/celery -A ccms.celery_app worker -Q net -c 20 -l info -n net@%h'
worker_stream: bash -c 'cd backend && .venv/bin/celery -A ccms.celery_app worker -Q stream -c 4 -l info -n stream@%h'
worker_misc:   bash -c 'cd backend && .venv/bin/celery -A ccms.celery_app worker -Q celery,notifications,reports -c 4 -l info -n misc@%h'
frontend:      bash -c 'cd frontend && npm run dev -- --host'
mailpit:       mailpit --smtp 127.0.0.1:1025 --listen 127.0.0.1:8025
mediamtx:      mediamtx simulator/mediamtx.yml
simulator:     bash -c 'cd simulator && ../backend/.venv/bin/python -m ccms_sim.cli run --count 8'
