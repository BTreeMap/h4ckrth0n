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


def get_app_routes() -> list[tuple[str, str, str]]:
    """Return (method, path, summary) tuples from the live FastAPI app via OpenAPI."""
    from h4ckath0n.app import create_app  # noqa: E402
    from h4ckath0n.config import Settings  # noqa: E402

    settings = Settings(
        database_url="sqlite+aiosqlite://",
        password_auth_enabled=True,
    )
    app = create_app(settings)

    routes: list[tuple[str, str, str]] = []
    paths = app.openapi().get("paths", {})
    for path, methods in paths.items():
        if path in FRAMEWORK_PATHS:
            continue
        for method, op in methods.items():
            if method.upper() == "HEAD":
                continue
            summary = op.get("summary", "")
            routes.append((method.upper(), path, summary))
    return sorted(routes)


def generate_routes_table(routes: list[tuple[str, str, str]]) -> str:
    """Generate markdown table for routes."""
    lines = ["| Method | Path | Summary |", "|---|---|---|"]
    for method, path, summary in routes:
        lines.append(f"| `{method}` | `{path}` | {summary} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Check or fix API route docs in README."
    )
    parser.add_argument(
        "--fix", action="store_true", help="Fix README.md automatically"
    )
    args = parser.parse_args()

    routes = get_app_routes()
    table = generate_routes_table(routes)

    readme_text = README.read_text()

    marker_start = "<!-- BEGIN API ROUTES -->\n"
    marker_end = "<!-- END API ROUTES -->\n"

    if marker_start not in readme_text or marker_end not in readme_text:
        print("❌ Markers not found in README.md. ")
        print("Please add <!-- BEGIN API ROUTES --> and <!-- END API ROUTES -->.")
        return 1

    before = readme_text.split(marker_start)[0]
    after = readme_text.split(marker_end)[1]

    new_readme_text = before + marker_start + table + marker_end + after

    if readme_text == new_readme_text:
        print(
            f"✅ All {len(routes)} API routes are documented accurately in README.md."
        )
        return 0

    if args.fix:
        README.write_text(new_readme_text)
        print("✅ Updated README.md with latest API routes.")
        return 0
    else:
        print("❌ API routes in README.md are outdated or drifting.")
        print("Run this script with --fix to automatically update them.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
