"""Ensures monthly RANGE partitions exist on check_results ahead of need
(replaces TimescaleDB's automatic chunking with an explicit equivalent,
see alembic/versions/0002_check_results.py)."""

from datetime import date

from sqlalchemy import text

from ccms.db import engine


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


def ensure_partitions(months_ahead: int = 3) -> list[str]:
    today = date.today()
    created = []
    with engine.begin() as conn:
        year, month = today.year, today.month
        for _ in range(months_ahead + 1):
            start, end = _month_bounds(year, month)
            partition_name = f"check_results_y{year}_m{month:02d}"
            conn.execute(
                text(
                    f"""
                    CREATE TABLE IF NOT EXISTS {partition_name}
                    PARTITION OF check_results
                    FOR VALUES FROM (:start) TO (:end)
                    """
                ),
                {"start": start, "end": end},
            )
            created.append(partition_name)
            month += 1
            if month > 12:
                month = 1
                year += 1
    return created
