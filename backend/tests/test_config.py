import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from backend.database import normalize_database_url
from backend.main import create_app, parse_origins

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _sandbox_repo(tmp_path: Path, dotenv_text: str) -> Path:
    """Copy the backend package next to a throwaway .env so the real repo is never touched."""
    shutil.copytree(
        BACKEND_DIR, tmp_path / "backend", ignore=shutil.ignore_patterns("tests", "__pycache__", "*.db")
    )
    (tmp_path / ".env").write_text(dotenv_text)
    return tmp_path


def test_missing_secret_key_fails_at_startup(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app()


def _run(code: str, cwd: Path):
    return subprocess.run(
        [sys.executable, "-c", code],
        env={"PATH": os.environ["PATH"]},
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def test_importing_app_modules_does_not_load_dotenv(tmp_path):
    """A .env next to the package must not leak into a plain import (e.g. under pytest)."""
    root = _sandbox_repo(tmp_path, "OPENAI_API_KEY=sk-from-dotenv\nDATABASE_URL=sqlite:////nonexistent/x.db\n")
    code = (
        "import os, backend.main, backend.auth, backend.database, backend.ai_client;"
        "print(os.getenv('OPENAI_API_KEY'), os.getenv('DATABASE_URL'))"
    )
    out = _run(code, root)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "None None"


def test_entry_point_loads_dotenv(tmp_path):
    root = _sandbox_repo(tmp_path, "SECRET_KEY=from-dotenv-0123456789\n")
    out = _run("import os, backend.main as m; m.app; print(os.getenv('SECRET_KEY'))", root)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "from-dotenv-0123456789"


@pytest.mark.parametrize(
    "raw, expected",
    [
        (None, ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000"]),
        ("https://app.vercel.app/", ["https://app.vercel.app"]),
        (" https://a.com/ , https://b.com// ,", ["https://a.com", "https://b.com"]),
    ],
)
def test_parse_origins(raw, expected):
    assert parse_origins(raw) == expected


@pytest.mark.parametrize(
    "url, expected",
    [
        ("postgres://u:p@host:5432/db", "postgresql://u:p@host:5432/db"),
        ("postgresql://u:p@host/db", "postgresql://u:p@host/db"),
        ("sqlite:///./x.db", "sqlite:///./x.db"),
    ],
)
def test_normalize_database_url(url, expected):
    assert normalize_database_url(url) == expected


@pytest.mark.parametrize("key", ["change-me", "short-key", "x" * 15])
def test_placeholder_or_short_secret_key_is_refused(monkeypatch, key):
    monkeypatch.setenv("SECRET_KEY", key)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app()


def test_16_character_secret_key_is_accepted(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "x" * 16)
    create_app()
