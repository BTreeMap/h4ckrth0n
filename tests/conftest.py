"""Common test fixtures and helpers."""

import os
import subprocess
import sys


def run_cli(*args: str, env_override: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    """Run the CLI via ``python -m h4ckath0n``."""
    env = os.environ.copy()
    if env_override:
        env.update(env_override)
    return subprocess.run(
        [sys.executable, "-m", "h4ckath0n", *args],
        capture_output=True,
        text=True,
        env=env,
    )
