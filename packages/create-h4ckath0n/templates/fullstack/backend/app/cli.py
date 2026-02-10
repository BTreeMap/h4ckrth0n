"""CLI for the scaffolded h4ckath0n project."""

from __future__ import annotations

import os
import subprocess
import sys


def main() -> None:
    """Entry point for the h4ckath0n CLI."""
    if len(sys.argv) < 2:
        _print_help()
        return

    command = sys.argv[1]
    handlers = {
        "dev": _cmd_dev,
        "help": _print_help,
    }

    handler = handlers.get(command)
    if handler:
        handler()
    else:
        print(f"Unknown command: {command}")
        _print_help()
        sys.exit(1)


def _cmd_dev() -> None:
    """Run backend and frontend dev servers concurrently."""
    project_root = _find_project_root()
    backend_dir = os.path.join(project_root, "backend")
    web_dir = os.path.join(project_root, "web")

    print("Starting h4ckath0n dev servers...")
    print(f"  Backend: http://localhost:8000 (from {backend_dir})")
    print(f"  Frontend: http://localhost:5173 (from {web_dir})")
    print()

    processes = []
    try:
        # Start backend
        backend_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"],
            cwd=backend_dir,
        )
        processes.append(backend_proc)

        # Start frontend
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
        frontend_proc = subprocess.Popen(
            [npm_cmd, "run", "dev"],
            cwd=web_dir,
        )
        processes.append(frontend_proc)

        # Wait for any process to exit
        for proc in processes:
            proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        for proc in processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except (subprocess.TimeoutExpired, OSError):
                proc.kill()


def _find_project_root() -> str:
    """Find the project root by looking for backend/ and web/ directories."""
    # Start from the current working directory
    cwd = os.getcwd()
    if os.path.isdir(os.path.join(cwd, "backend")) and os.path.isdir(os.path.join(cwd, "web")):
        return cwd
    # Try parent of backend/
    parent = os.path.dirname(cwd)
    if os.path.isdir(os.path.join(parent, "backend")) and os.path.isdir(
        os.path.join(parent, "web")
    ):
        return parent
    # Default to cwd
    return cwd


def _print_help() -> None:
    """Print CLI help."""
    print("h4ckath0n backend CLI")
    print()
    print("Usage: uv run h4ckath0n <command>")
    print("  (run from the backend/ directory of your scaffolded project)")
    print()
    print("Commands:")
    print("  dev     Start backend and frontend dev servers")
    print("  help    Show this help message")
