#!/usr/bin/env -S uv run python
"""Drift-prevention check: verify that every API route in the FastAPI app is documented.

Usage (from repo root):
    uv run scripts/check_doc_routes.py

The script imports the h4ckath0n app, enumerates all routes, and checks that
README.md mentions each one. Routes provided by FastAPI itself (e.g. /openapi.json,
/docs, /redoc) are excluded from the check.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"

# FastAPI paths omitted from user docs.
FRAMEWORK_PATHS = frozenset(
    {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}
)


def get_app_routes_with_descriptions() -> list[tuple[str, str, str]]:
    """Return (method, path, summary) tuples from the live FastAPI app."""
    from h4ckath0n.app import create_app  # noqa: E402
    from h4ckath0n.config import Settings  # noqa: E402

    settings = Settings(
        database_url="sqlite+aiosqlite://",
        password_auth_enabled=True,
    )
    app = create_app(settings)

    routes: list[tuple[str, str, str]] = []
    paths = app.openapi().get("paths", {})
    for path, path_item in paths.items():
        if path in FRAMEWORK_PATHS:
            continue
        for method, op in sorted(path_item.items()):
            if method not in {
                "get",
                "put",
                "post",
                "delete",
                "options",
                "head",
                "patch",
                "trace",
            }:
                continue
            method_upper = method.upper()
            if method_upper == "HEAD":
                continue
            summary = op.get("summary", "")
            routes.append((method_upper, path, summary))
    return sorted(routes)


def generate_routes_table(routes: list[tuple[str, str, str]]) -> str:
    """Generate a Markdown table for the given routes."""
    lines = [
        "| Method | Path | Description |",
        "|---|---|---|",
    ]
    for method, path, summary in routes:
        lines.append(f"| `{method}` | `{path}` | {summary} |")
    return "\n".join(lines)


def main() -> int:
    routes = get_app_routes_with_descriptions()
    table = generate_routes_table(routes)

    readme_text = README.read_text()

    begin_marker = "<!-- BEGIN API ROUTES -->"
    end_marker = "<!-- END API ROUTES -->"

    if begin_marker not in readme_text or end_marker not in readme_text:
        print("❌ README.md is missing the API ROUTES markers.")
        return 1

    start_idx = readme_text.find(begin_marker) + len(begin_marker)
    end_idx = readme_text.find(end_marker)

    current_content = readme_text[start_idx:end_idx].strip()

    if current_content == table:
        print(f"✅ All {len(routes)} API routes are documented correctly in README.md.")
        return 0

    if "--update" in sys.argv:
        new_text = readme_text[:start_idx] + "\n" + table + "\n" + readme_text[end_idx:]
        README.write_text(new_text)
        print("✅ README.md has been updated with the latest API routes.")
        return 0
    else:
        print("❌ README.md API routes are out of date.")
        print("Run `uv run python scripts/check_doc_routes.py --update` to fix.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
