from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Anchored to this file (backend/ccms/config.py -> repo root/.env), not to the
# process CWD - CWD varies between `cd backend && uvicorn ...` (Procfile) and
# scripts run from the repo root (scripts/seed_admin_user.py etc).
_REPO_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CCMS_", env_file=str(_REPO_ROOT_ENV), extra="ignore")

    database_url: str = "postgresql+psycopg://localhost/ccms"

    redis_broker_url: str = "redis://localhost:6379/0"
    redis_backend_url: str = "redis://localhost:6379/1"

    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30

    cred_enc_key: str = "changeme-base64-32-bytes"

    # email_transport=smtp connects directly to smtp_host:smtp_port (Mailpit in
    # dev). email_transport=msmtp instead pipes the message through the local
    # `msmtp` binary, which relays using whatever's configured in
    # /etc/msmtprc - the standard way to send mail from a server that already
    # has a local MTA/relay set up (see deploy/msmtprc.template).
    email_transport: str = "smtp"
    msmtp_binary: str = "msmtp"
    msmtp_account: str = "default"

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_pass: str = ""
    smtp_from: str = "ccms@campus.local"
    smtp_tls: bool = False

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""

    whatsapp_webhook_url: str = ""
    whatsapp_api_token: str = ""

    sim_control_url: str = "http://127.0.0.1:9500"
    sim_rtsp_base: str = "rtsp://127.0.0.1:8554"

    serve_frontend_dist: bool = False
    log_level: str = "INFO"

    # Debounce defaults (FR-06), overridable per device via settings table later
    debounce_down_count: int = 3
    debounce_up_count: int = 2


settings = Settings()
