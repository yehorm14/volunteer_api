"""Public, read-only sample workspace.

Enabled only when both DEMO_USER_EMAIL and DEMO_PUBLIC=1 are set. Visitors get a token for the
shared demo user without a password (POST /auth/demo); that user can read its sample tasks but
every write, and the AI endpoints, answer 403. Nothing a visitor does can change or leak data,
so no per-visitor copy is needed. Delete DEMO_PUBLIC to turn it off.
"""
import os

from . import models

READ_ONLY_DETAIL = "This is a read-only sample workspace. Create an account to add or change tasks."


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def demo_email() -> str:
    return os.getenv("DEMO_USER_EMAIL", "").strip().lower()


def is_public_demo_enabled() -> bool:
    return bool(demo_email()) and _truthy(os.getenv("DEMO_PUBLIC"))


def is_demo_user(user: models.User) -> bool:
    return is_public_demo_enabled() and user.email == demo_email()  # type: ignore[comparison-overlap]
