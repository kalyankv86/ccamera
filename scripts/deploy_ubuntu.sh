#!/usr/bin/env bash
# Provisions CCMS on a fresh Ubuntu server. Targets 24.04 LTS "noble" but
# also handles 22.04/20.04 by pulling Python 3.12 from deadsnakes when it's
# not in the default repos.
# Run as a regular sudo-capable user, or as root (e.g. a bare cloud VM with
# no other user set up yet) - both work:
#   git clone https://github.com/kalyankv86/ccamera.git && cd ccamera
#   ./scripts/deploy_ubuntu.sh
#
# This installs system packages, creates a dedicated `ccms` service user,
# copies the app to /opt/ccms, builds the frontend, runs migrations, installs
# systemd units for the API/beat/3 workers, and configures Nginx.
#
# NOT installed here: mediamtx or the simulator - those are dev/demo-only
# tools for exercising the pipeline without physical cameras. Production
# points the device registry at real camera/NVR IP addresses instead.
#
# You will be prompted for the domain name (for Nginx + certbot) and whether
# to run certbot now, unless CCMS_DEPLOY_DOMAIN / CCMS_DEPLOY_RUN_CERTBOT are
# already set in the environment (for non-interactive/scripted runs).
# Everything else (secrets, DB password) is generated. Idempotent-ish: safe
# to re-run, but review before doing so on an already-live install (it does
# not stop running services first).
set -euo pipefail

APP_DIR=/opt/ccms
SERVICE_USER=ccms
REPO_SOURCE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [ "$(id -u)" -eq 0 ]; then
  echo "==> Running as root (sudo run by root doesn't prompt, so this works fine)"
fi

DOMAIN="${CCMS_DEPLOY_DOMAIN:-}"
if [ -z "$DOMAIN" ]; then
  read -rp "Domain name this server will be reachable at (e.g. ccms.yourcampus.edu): " DOMAIN
fi
RUN_CERTBOT="${CCMS_DEPLOY_RUN_CERTBOT:-}"
if [ -z "$RUN_CERTBOT" ]; then
  read -rp "Run certbot for a real TLS certificate now? [y/N]: " RUN_CERTBOT
fi

echo "==> Installing system packages"
# DEBIAN_FRONTEND=noninteractive must be passed as part of the sudo command
# itself (sudo VAR=val cmd), not just exported in this shell - sudo's default
# env_reset policy strips inherited env vars unless they're set this way or
# via sudo -E. Without this, packages with a postinst debconf question (e.g.
# msmtp's AppArmor prompt) fall back to a Readline prompt with no TTY behind
# it and hang forever - confirmed the hard way on a real run.
export DEBIAN_FRONTEND=noninteractive
sudo DEBIAN_FRONTEND=noninteractive apt-get update -y

# Ubuntu 24.04 "noble" ships python3.12 in the default repos; older releases
# (22.04 "jammy", 20.04 "focal") don't, so pull it from the deadsnakes PPA
# instead of failing outright.
if ! apt-cache show python3.12 >/dev/null 2>&1; then
  echo "==> python3.12 not in default repos - adding deadsnakes PPA"
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y software-properties-common
  sudo add-apt-repository -y ppa:deadsnakes/ppa
  sudo DEBIAN_FRONTEND=noninteractive apt-get update -y
fi

sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  python3.12 python3.12-venv python3-pip \
  postgresql postgresql-contrib \
  redis-server \
  ffmpeg \
  nginx \
  msmtp msmtp-mta \
  git build-essential libpq-dev rsync openssl \
  curl ca-certificates gnupg \
  certbot python3-certbot-nginx

if ! command -v node >/dev/null 2>&1; then
  echo "==> Installing Node.js 20.x (NodeSource)"
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y nodejs
fi

echo "==> Creating service user '$SERVICE_USER'"
if ! id "$SERVICE_USER" &>/dev/null; then
  sudo useradd --system --create-home --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
fi

echo "==> Copying application to $APP_DIR"
sudo mkdir -p "$APP_DIR"
sudo rsync -a --delete \
  --exclude '.git' --exclude '**/__pycache__' --exclude '**/.venv' \
  --exclude 'frontend/node_modules' --exclude 'frontend/dist' \
  --exclude '.env' \
  "$REPO_SOURCE_DIR"/ "$APP_DIR"/
sudo chown -R "$SERVICE_USER":"$SERVICE_USER" "$APP_DIR"

echo "==> Creating backend virtualenv"
sudo -u "$SERVICE_USER" python3.12 -m venv "$APP_DIR/backend/.venv"
sudo -u "$SERVICE_USER" "$APP_DIR/backend/.venv/bin/pip" install --upgrade pip -q
sudo -u "$SERVICE_USER" "$APP_DIR/backend/.venv/bin/pip" install -e "$APP_DIR/backend" -q

# First-time setup only, from here on: the rsync above excludes .env, so a
# re-run (e.g. to deploy updated code) leaves an existing production .env
# untouched. Regenerating CCMS_CRED_ENC_KEY on a re-run would make every
# already-stored device credential undecryptable, and regenerating the DB
# password without also updating the Postgres role would just break the
# connection - so if .env is already there, skip straight to migrations.
if [ -f "$APP_DIR/.env" ]; then
  echo "==> $APP_DIR/.env already exists - preserving it, skipping secret/DB-role generation"
else
  echo "==> Setting up PostgreSQL role and database"
  # hex, not base64: base64's +/= characters would need percent-encoding to
  # be valid inside the postgresql:// URL below, and it's easy to forget that.
  DB_PASSWORD="$(openssl rand -hex 24)"
  sudo -u postgres psql -c "CREATE ROLE ccms WITH LOGIN PASSWORD '${DB_PASSWORD}';"
  sudo -u postgres createdb -O ccms ccms

  echo "==> Generating production .env"
  JWT_SECRET="$(openssl rand -base64 48)"
  CRED_ENC_KEY="$(python3 -c 'import base64, os; print(base64.b64encode(os.urandom(32)).decode())')"
  sudo -u "$SERVICE_USER" bash -c "cat > '$APP_DIR/.env'" <<EOF
CCMS_DATABASE_URL=postgresql+psycopg://ccms:${DB_PASSWORD}@localhost/ccms

CCMS_REDIS_BROKER_URL=redis://localhost:6379/0
CCMS_REDIS_BACKEND_URL=redis://localhost:6379/1

CCMS_JWT_SECRET=${JWT_SECRET}
CCMS_JWT_ALGORITHM=HS256
CCMS_ACCESS_TOKEN_MINUTES=30

CCMS_CRED_ENC_KEY=${CRED_ENC_KEY}

CCMS_EMAIL_TRANSPORT=msmtp
CCMS_MSMTP_BINARY=msmtp
CCMS_MSMTP_ACCOUNT=default
CCMS_SMTP_FROM=ccms@${DOMAIN}

CCMS_TWILIO_ACCOUNT_SID=
CCMS_TWILIO_AUTH_TOKEN=
CCMS_TWILIO_FROM_NUMBER=

CCMS_WHATSAPP_WEBHOOK_URL=
CCMS_WHATSAPP_API_TOKEN=

CCMS_SERVE_FRONTEND_DIST=false
CCMS_LOG_LEVEL=INFO
EOF
  sudo chmod 640 "$APP_DIR/.env"
  sudo chown "$SERVICE_USER":"$SERVICE_USER" "$APP_DIR/.env"
fi

echo "==> Setting up msmtp (fill in your real relay before mail will send)"
if [ ! -f /etc/msmtprc ]; then
  sudo cp "$APP_DIR/deploy/msmtprc.template" /etc/msmtprc
fi
sudo chown root:"$SERVICE_USER" /etc/msmtprc
sudo chmod 640 /etc/msmtprc
sudo touch /var/log/msmtp.log
sudo chown "$SERVICE_USER":"$SERVICE_USER" /var/log/msmtp.log

echo "==> Running database migrations"
sudo -u "$SERVICE_USER" bash -c "cd '$APP_DIR/backend' && .venv/bin/alembic upgrade head"

echo "==> Seeding admin user"
sudo -u "$SERVICE_USER" bash -c "cd '$APP_DIR' && backend/.venv/bin/python scripts/seed_admin_user.py"

echo "==> Building frontend"
(cd "$APP_DIR/frontend" && sudo -u "$SERVICE_USER" npm ci && sudo -u "$SERVICE_USER" npm run build)

echo "==> Installing systemd units"
sudo cp "$APP_DIR"/deploy/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
for svc in ccms-api ccms-beat ccms-worker-net ccms-worker-stream ccms-worker-misc; do
  sudo systemctl enable "$svc"
  # restart, not start: `enable --now`/`start` is a no-op on an
  # already-running unit, which silently leaves a redeploy's new code
  # unloaded in the running process - confirmed the hard way live, where a
  # checker fix landed on disk but the already-running Celery worker kept
  # executing the old buggy version from memory until restarted by hand.
  sudo systemctl restart "$svc"
done

echo "==> Configuring Nginx"
sudo bash -c "sed 's/YOUR_DOMAIN/${DOMAIN}/g' '$APP_DIR/deploy/nginx/ccms.conf.template' > /etc/nginx/sites-available/ccms.conf"
sudo ln -sf /etc/nginx/sites-available/ccms.conf /etc/nginx/sites-enabled/ccms.conf
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx

if [[ "$RUN_CERTBOT" =~ ^[Yy]$ ]]; then
  echo "==> Requesting TLS certificate via certbot"
  sudo certbot --nginx -d "$DOMAIN"
else
  echo "==> Skipped certbot. Run later with: sudo certbot --nginx -d $DOMAIN"
fi

echo ""
echo "============================================================"
echo "Deployed. Next steps:"
echo "  1. Edit /etc/msmtprc with your real SMTP relay credentials,"
echo "     then test: echo -e 'Subject: test\n\nhi' | sudo -u $SERVICE_USER msmtp -a default you@example.com"
echo "  2. Log in at https://${DOMAIN}/ as admin@ccms.campus / ChangeMe123!"
echo "     and change that password immediately."
echo "  3. Register real devices via the Admin/Devices UI or CSV import."
echo "  4. Consider a firewall (ufw) restricting inbound to 80/443/22 only"
echo "     (NFR-11) - camera/NVR traffic stays on the LAN, only the"
echo "     dashboard needs to be reachable from staff networks."
echo "============================================================"
