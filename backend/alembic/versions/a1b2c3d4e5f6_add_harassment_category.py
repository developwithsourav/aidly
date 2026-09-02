"""add harassment category

The requirement set and the use cases have always included a personal safety
category. The enum did not, so a report of that kind had to be filed as
"other" and lost its identity in the incident feed.

Revision ID: a1b2c3d4e5f6
Revises: c5802b0e6f36
Created: 2026-09-03
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "c5802b0e6f36"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ENUM = "incident_category"
# The order the type is rebuilt in on downgrade. Must match the model.
WITHOUT_HARASSMENT = ("fire", "medical", "crowd", "accident", "violence",
                      "other")


def _columns_using(conn, type_name: str) -> list[tuple[str, str]]:
    """Every table and column that uses the type, read from the catalogue.

    Hardcoding this list is how the first version of this migration went wrong:
    it named incidents and reports and forgot protocols, so the downgrade died
    part way through. Asking the database removes the chance of missing one.
    """
    rows = conn.execute(sa.text("""
        SELECT c.relname, a.attname
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_type t ON t.oid = a.atttypid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE t.typname = :name
          AND c.relkind = 'r'
          AND a.attnum > 0
          AND NOT a.attisdropped
          AND n.nspname = current_schema()
        ORDER BY c.relname, a.attname
    """), {"name": type_name}).fetchall()
    return [(r[0], r[1]) for r in rows]


def upgrade() -> None:
    # PostgreSQL will not let a value added to an enum be used in the same
    # transaction that added it, so this runs outside the migration's
    # transaction. IF NOT EXISTS keeps the migration safe to re run.
    with op.get_context().autocommit_block():
        op.execute(f"ALTER TYPE {ENUM} ADD VALUE IF NOT EXISTS 'harassment'")


def downgrade() -> None:
    """Rebuild the type without the value.

    PostgreSQL cannot drop a single enum label, so the type is recreated and
    the columns are moved across. Any row already using the value would block
    that, so those rows are moved to "other" first. That loses information,
    which is the honest cost of reversing this migration rather than a reason
    to pretend the downgrade is free.
    """
    conn = op.get_bind()
    using = _columns_using(conn, ENUM)

    for table, column in using:
        op.execute(
            f"UPDATE {table} SET {column} = 'other' "
            f"WHERE {column} = 'harassment'"
        )

    values = ", ".join(f"'{v}'" for v in WITHOUT_HARASSMENT)
    op.execute(f"ALTER TYPE {ENUM} RENAME TO {ENUM}_old")
    op.execute(f"CREATE TYPE {ENUM} AS ENUM ({values})")
    for table, column in using:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} "
            f"TYPE {ENUM} USING {column}::text::{ENUM}"
        )
    op.execute(f"DROP TYPE {ENUM}_old")
