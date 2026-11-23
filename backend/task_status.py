"""The single backend definition of the task status contract.

The frontend mirrors these values in frontend/src/types/index.ts; a test keeps the two in sync.
"""
from typing import Literal, get_args

from sqlalchemy import text
from sqlalchemy.engine import Engine

TaskStatus = Literal["pending", "in_progress", "completed"]
TASK_STATUSES: tuple[str, ...] = get_args(TaskStatus)
DEFAULT_STATUS: TaskStatus = "pending"

# Migration policy for rows that predate the contract (hand-edited data, older clients):
#   * known spellings are mapped to the canonical value,
#   * anything unrecognised, empty or NULL becomes "pending",
#   * rows are never deleted.
_LEGACY_ALIASES: dict[str, str] = {
    "todo": "pending",
    "to_do": "pending",
    "open": "pending",
    "new": "pending",
    "inprogress": "in_progress",
    "doing": "in_progress",
    "started": "in_progress",
    "done": "completed",
    "complete": "completed",
    "closed": "completed",
    "finished": "completed",
}


def normalize_legacy_status(value: str | None) -> str:
    """Map any stored status to a canonical one (see the policy above)."""
    if value is None:
        return DEFAULT_STATUS
    key = "_".join(value.strip().lower().replace("-", " ").split())
    if key in TASK_STATUSES:
        return key
    return _LEGACY_ALIASES.get(key, DEFAULT_STATUS)


def normalize_task_statuses(engine: Engine) -> int:
    """Rewrite non-canonical status values in place. Idempotent; returns the number of rows changed."""
    placeholders = ", ".join(f":s{i}" for i in range(len(TASK_STATUSES)))
    params = {f"s{i}": s for i, s in enumerate(TASK_STATUSES)}
    changed = 0
    with engine.begin() as conn:
        rows = conn.execute(
            text(f"SELECT id, status FROM tasks WHERE status IS NULL OR status NOT IN ({placeholders})"),
            params,
        ).all()
        for task_id, old in rows:
            conn.execute(
                text("UPDATE tasks SET status = :new WHERE id = :id"),
                {"new": normalize_legacy_status(old), "id": task_id},
            )
            changed += 1
    return changed
