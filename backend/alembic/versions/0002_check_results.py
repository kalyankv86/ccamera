"""check_results partitioned table + check_results_daily aggregate.

Hand-written (not autogenerate): declarative RANGE partitioning isn't
supported by Alembic's autogenerate, and this table replaces the SDD's
TimescaleDB hypertable with a plain-Postgres equivalent.

Revision ID: 0002_check_results
Revises: 0001_initial
Create Date: 2026-08-01
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_check_results"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE check_results (
            id BIGSERIAL,
            time TIMESTAMPTZ NOT NULL,
            device_id INTEGER NOT NULL REFERENCES devices(id),
            check_type VARCHAR(16) NOT NULL,
            status VARCHAR(16) NOT NULL,
            latency_ms NUMERIC(10, 2),
            loss_pct NUMERIC(5, 2),
            metrics_jsonb JSONB,
            maintenance_flag BOOLEAN NOT NULL DEFAULT FALSE,
            PRIMARY KEY (id, time)
        ) PARTITION BY RANGE (time);
        """
    )
    op.execute("CREATE INDEX ix_check_results_device_time ON check_results (device_id, time DESC);")
    op.execute("CREATE INDEX ix_check_results_type_time ON check_results (check_type, time DESC);")

    # Default partition catches anything outside the pre-created monthly range
    # (e.g. clock skew, late-arriving jobs) so inserts never fail outright.
    op.execute("CREATE TABLE check_results_default PARTITION OF check_results DEFAULT;")

    op.create_table(
        "check_results_daily",
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), primary_key=True),
        sa.Column("day", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("check_type", sa.String(16), primary_key=True),
        sa.Column("samples", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("up_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fail_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("degraded_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_latency_ms", sa.Numeric(10, 2)),
        sa.Column("avg_loss_pct", sa.Numeric(5, 2)),
    )


def downgrade() -> None:
    op.drop_table("check_results_daily")
    op.execute("DROP TABLE IF EXISTS check_results CASCADE;")
