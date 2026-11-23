"""Per-user daily cap on AI calls, shared by /tasks/extract and /tasks/{id}/ai-categorize.

The counter lives in the ai_usage table (one row per user and UTC day), so it survives restarts
and is shared by every API process. The day rolls over at 00:00 UTC.
"""
import os
from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models
from .deps import DB, WritableUser

DEFAULT_AI_DAILY_LIMIT = 20


def utc_now() -> datetime:
    """Replaced in tests with a fake clock."""
    return datetime.now(timezone.utc)


def daily_limit() -> int:
    raw = os.getenv("AI_DAILY_LIMIT")
    if raw is None or not raw.strip():
        return DEFAULT_AI_DAILY_LIMIT
    try:
        value = int(raw)
    except ValueError:
        value = 0
    if value < 1:
        raise RuntimeError(f"AI_DAILY_LIMIT must be a positive integer, got {raw!r}.")
    return value


def _today() -> date:
    return utc_now().date()


def _try_increment(db: Session, user_id: int, day: date, limit: int) -> bool:
    """Atomically add one if the user is below the limit. False when the row is missing or full."""
    result = db.execute(
        update(models.AiUsage)
        .where(models.AiUsage.user_id == user_id, models.AiUsage.day == day, models.AiUsage.count < limit)
        .values(count=models.AiUsage.count + 1)
    )
    return result.rowcount == 1


def consume(db: Session, user_id: int) -> date:
    """Count one AI call for today, or raise 429. Returns the day charged (for refund)."""
    limit = daily_limit()
    day = _today()
    if not _try_increment(db, user_id, day, limit):
        exists = db.query(models.AiUsage).filter_by(user_id=user_id, day=day).first()
        if exists is not None:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Daily AI limit reached ({limit} per day). It resets at midnight UTC.",
            )
        try:
            db.add(models.AiUsage(user_id=user_id, day=day, count=1))
            db.flush()
        except IntegrityError:  # a concurrent request created today's row first
            db.rollback()
            if not _try_increment(db, user_id, day, limit):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Daily AI limit reached ({limit} per day). It resets at midnight UTC.",
                )
    db.commit()
    return day


def refund(db: Session, user_id: int, day: date) -> None:
    """Give back one call when the provider failed, so an outage does not eat the quota."""
    db.execute(
        update(models.AiUsage)
        .where(models.AiUsage.user_id == user_id, models.AiUsage.day == day, models.AiUsage.count > 0)
        .values(count=models.AiUsage.count - 1)
    )
    db.commit()


def charge_ai_call(user: WritableUser, db: DB) -> tuple[int, date]:
    """Dependency: spends one of the user's daily AI calls (429 when none are left)."""
    user_id: int = user.id  # type: ignore[assignment]
    return user_id, consume(db, user_id)


AiCharge = Annotated[tuple[int, date], Depends(charge_ai_call)]
