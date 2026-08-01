from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from ccms.config import settings
from ccms.db import Base
from ccms import models  # noqa: F401  (registers all model metadata)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata

# check_results/check_results_daily are hand-authored in 0002_check_results.py
# (native RANGE partitioning isn't expressible via autogenerate) - exclude them
# from the diff entirely so autogenerate never tries to (re)create them.
_HAND_MANAGED_TABLES = {"check_results", "check_results_daily"}


def include_object(obj, name, type_, reflected, compare_to):
    if type_ == "table" and name in _HAND_MANAGED_TABLES:
        return False
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True, compare_type=True, include_object=include_object
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, compare_type=True, include_object=include_object
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
