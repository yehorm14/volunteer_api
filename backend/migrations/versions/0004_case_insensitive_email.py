"""Case-insensitive unique emails: lower-case existing rows and index lower(email).

Revision ID: 0004
Revises: 0003

Existing rows that differ only by case (A@x.com and a@x.com) would collide once lower-cased.
Nothing is deleted and no tasks move. For each such group the oldest account (lowest id) keeps
the plain lower-cased address; every other account is deactivated and renamed to
``<local>+duplicate-<id>@<domain>`` with a numeric suffix if that address is taken. It keeps its tasks and password and can be
found and merged or removed by hand. Each rename is logged.
"""
import logging
import os

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

INDEX_NAME = "uq_users_email_lower"
log = logging.getLogger("alembic.runtime.migration")


def _duplicate_name(lowered: str, user_id: int, reserved: set[str]) -> str:
    local, at, domain = lowered.rpartition("@")
    prefix = f"{local if at else lowered}+duplicate-{user_id}"
    suffix = f"@{domain}" if at else ""
    candidate = prefix + suffix
    index = 2
    while candidate in reserved:
        candidate = f"{prefix}-{index}{suffix}"
        index += 1
    reserved.add(candidate)
    return candidate


def upgrade() -> None:
    bind = op.get_bind()
    # SQLite's legacy transaction mode does not start a transaction for ALTER TABLE.
    if bind.dialect.name == "sqlite" and not bind.connection.driver_connection.in_transaction:
        bind.exec_driver_sql("BEGIN IMMEDIATE")
    op.add_column("users", sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()))
    # A public workspace can only retain the exact identity that the old endpoint used.
    public_demo_enabled = os.getenv("DEMO_PUBLIC", "").strip().lower() in {"1", "true", "yes", "on"}
    demo_email = os.getenv("DEMO_USER_EMAIL", "").strip() if public_demo_enabled else ""
    # lower() is evaluated by the database itself so the grouping matches the index below exactly.
    rows = bind.execute(sa.text("SELECT id, email, lower(email) FROM users WHERE email IS NOT NULL ORDER BY id")).all()
    reserved = {lowered for _, _, lowered in rows}
    seen: set[str] = set()
    keepers: list[tuple[int, str]] = []
    # Rename the losers first: a keeper's lower-cased address may equal a loser's current address.
    for user_id, email, lowered in rows:
        if lowered in seen:
            renamed = _duplicate_name(lowered, user_id, reserved)
            log.warning("users.id=%s email %r duplicates an earlier account when ignoring case; renamed to %r and deactivated", user_id, email, renamed)
            bind.execute(
                sa.text("UPDATE users SET email = :email, is_active = :inactive WHERE id = :id"),
                {"email": renamed, "inactive": False, "id": user_id},
            )
        else:
            seen.add(lowered)
            if demo_email and email == demo_email:
                bind.execute(
                    sa.text("UPDATE users SET is_demo = :is_demo WHERE id = :id AND is_active"),
                    {"is_demo": True, "id": user_id},
                )
            if email != lowered:
                keepers.append((user_id, lowered))
    for user_id, lowered in keepers:
        bind.execute(sa.text("UPDATE users SET email = :email WHERE id = :id"), {"email": lowered, "id": user_id})
    op.create_index(INDEX_NAME, "users", [sa.text("lower(email)")], unique=True)


def downgrade() -> None:
    # Lower-cased addresses and renamed duplicates are not restored.
    op.drop_index(INDEX_NAME, table_name="users")
    op.drop_column("users", "is_demo")
