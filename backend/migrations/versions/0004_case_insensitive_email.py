"""Case-insensitive unique emails: lower-case existing rows and index lower(email).

Revision ID: 0004
Revises: 0003

Existing rows that differ only by case (A@x.com and a@x.com) would collide once lower-cased.
Nothing is deleted and no tasks move. For each such group the oldest account (lowest id) keeps
the plain lower-cased address; every other account is deactivated and renamed to
``<local>+duplicate-<id>@<domain>`` so it stays unique, keeps its tasks and password, and can be
found and merged or removed by hand. Each rename is logged.
"""
import logging

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

INDEX_NAME = "uq_users_email_lower"
log = logging.getLogger("alembic.runtime.migration")


def _duplicate_name(lowered: str, user_id: int) -> str:
    local, at, domain = lowered.rpartition("@")
    if not at:
        return f"{lowered}+duplicate-{user_id}"
    return f"{local}+duplicate-{user_id}@{domain}"


def upgrade() -> None:
    bind = op.get_bind()
    # lower() is evaluated by the database itself so the grouping matches the index below exactly.
    rows = bind.execute(sa.text("SELECT id, email, lower(email) FROM users WHERE email IS NOT NULL ORDER BY id")).all()
    seen: set[str] = set()
    keepers: list[tuple[int, str]] = []
    # Rename the losers first: a keeper's lower-cased address may equal a loser's current address.
    for user_id, email, lowered in rows:
        if lowered in seen:
            renamed = _duplicate_name(lowered, user_id)
            log.warning("users.id=%s email %r duplicates an earlier account when ignoring case; renamed to %r and deactivated", user_id, email, renamed)
            bind.execute(
                sa.text("UPDATE users SET email = :email, is_active = :inactive WHERE id = :id"),
                {"email": renamed, "inactive": False, "id": user_id},
            )
        else:
            seen.add(lowered)
            if email != lowered:
                keepers.append((user_id, lowered))
    for user_id, lowered in keepers:
        bind.execute(sa.text("UPDATE users SET email = :email WHERE id = :id"), {"email": lowered, "id": user_id})
    op.create_index(INDEX_NAME, "users", [sa.text("lower(email)")], unique=True)


def downgrade() -> None:
    # Lower-cased addresses and renamed duplicates are not restored.
    op.drop_index(INDEX_NAME, table_name="users")
