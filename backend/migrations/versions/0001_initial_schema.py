"""Initial schema: users and tasks, exactly as create_all() built them before migrations.

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String()),
        sa.Column("hashed_password", sa.String()),
        sa.Column("is_active", sa.Boolean()),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String()),
        sa.Column("description", sa.String()),
        sa.Column("status", sa.String()),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id")),
    )
    op.create_index("ix_tasks_id", "tasks", ["id"])
    op.create_index("ix_tasks_title", "tasks", ["title"])
    op.create_index("ix_tasks_description", "tasks", ["description"])


def downgrade() -> None:
    op.drop_table("tasks")
    op.drop_table("users")
