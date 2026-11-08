import subprocess
import sys


def test_missing_secret_key_fails_at_startup():
    # Empty value wins over any .env file (load_dotenv does not override existing vars).
    env = {"PATH": "/usr/bin:/bin", "SECRET_KEY": ""}
    result = subprocess.run(
        [sys.executable, "-c", "import backend.auth"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "SECRET_KEY" in result.stderr
