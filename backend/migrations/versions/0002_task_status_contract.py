"""Repair legacy task rows, then enforce the status contract in the database.

Rows are never deleted: statuses are normalised (see backend/task_status.py for the policy),
a missing or blank title becomes "(untitled)", and only then are NOT NULL and the CHECK added.

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

from backend.task_status import TASK_STATUSES, normalize_task_statuses

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

CONSTRAINT = "ck_tasks_status"


def upgrade() -> None:
    conn = op.get_bind()
    normalize_task_statuses(conn)
    conn.execute(sa.text("UPDATE tasks SET title = '(untitled)' WHERE title IS NULL OR TRIM(title) = ''"))
    with op.batch_alter_table("tasks") as batch:
        batch.alter_column("title", existing_type=sa.String(), nullable=False)
        batch.alter_column("status", existing_type=sa.String(), nullable=False)
        batch.create_check_constraint(CONSTRAINT, "status IN (" + ", ".join(f"'{s}'" for s in TASK_STATUSES) + ")")


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch:
        batch.drop_constraint(CONSTRAINT, type_="check")
        batch.alter_column("status", existing_type=sa.String(), nullable=True)
        batch.alter_column("title", existing_type=sa.String(), nullable=True)
