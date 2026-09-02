"""Alembic environment.

The database URL comes from app.config rather than alembic.ini, so there is
exactly one place a connection string is configured and none of them is a file
that gets committed.
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import get_settings
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", str(get_settings().database_url))
target_metadata = Base.metadata

# PostGIS installs its own tables and indexes into the same schema. They are not
# ours to manage, and without this filter every autogenerate would try to drop
# them.
POSTGIS_TABLES = {
    "spatial_ref_sys", "geography_columns", "geometry_columns",
    "raster_columns", "raster_overviews",
}


def include_object(obj, name, type_, reflected, compare_to):
    if type_ == "table" and name in POSTGIS_TABLES:
        return False
    # geoalchemy2 creates a spatial index as a side effect of creating a
    # Geography column, naming it idx_<table>_<column>. Alembic sees it in the
    # model metadata and emits a second CREATE INDEX, which fails as a
    # duplicate. Our own indexes all use SQLAlchemy's ix_ prefix, so skipping
    # idx_ leaves geoalchemy2 to manage its own and us to manage ours.
    if type_ == "index" and name and name.startswith("idx_"):
        return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        include_object=include_object,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
