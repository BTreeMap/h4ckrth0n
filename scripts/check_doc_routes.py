#!/usr/bin/env -S uv run python
"""Drift-prevention check: verify that every API route in the FastAPI app is documented.

Usage (from repo root):
    uv run scripts/check_doc_routes.py [--fix]

The script imports the h4ckath0n app, enumerates all routes using the OpenAPI schema,
and checks that README.md documents each one in a generated table between
<!-- BEGIN API ROUTES --> and <!-- END API ROUTES -->.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"

MARKER_BEGIN = "<!-- BEGIN API ROUTES -->"
MARKER_END = "<!-- END API ROUTES -->"


def get_app_routes() -> list[tuple[str, str, str]]:
    """Return (method, path, summary) from the live FastAPI app's OpenAPI schema."""
    from h4ckath0n.app import create_app  # noqa: E402
    from h4ckath0n.config import Settings  # noqa: E402

    settings = Settings(
        database_url="sqlite+aiosqlite://",
        password_auth_enabled=True,
    )
    app = create_app(settings)

    schema = app.openapi()
    paths = schema.get("paths", {})

    routes: list[tuple[str, str, str]] = []
    for path, methods in paths.items():
        for method, op in methods.items():
            routes.append((method.upper(), path, op.get("summary", "")))
    return sorted(routes, key=lambda x: (x[1], x[0]))


def generate_routes_table(routes: list[tuple[str, str, str]]) -> str:
    """Generate the markdown table for routes."""
    lines = [
        "| Method | Path | Summary |",
        "|---|---|---|",
    ]
    for method, path, summary in routes:
        lines.append(f"| `{method}` | `{path}` | {summary} |")
    return "\n".join(lines)


def check_routes_in_readme(routes: list[tuple[str, str, str]], fix: bool) -> int:
    """Check or fix the routes table in README.md."""
    readme_text = README.read_text()

    if MARKER_BEGIN not in readme_text or MARKER_END not in readme_text:
        print(
            "❌ Markers <!-- BEGIN API ROUTES --> and <!-- END API ROUTES --> "
            "not found in README.md."
        )
        return 1

    before_marker = readme_text.split(MARKER_BEGIN)[0]
    after_marker = readme_text.split(MARKER_END)[1]

    expected_table = generate_routes_table(routes)
    expected_content = (
        f"{before_marker}{MARKER_BEGIN}\n{expected_table}\n{MARKER_END}{after_marker}"
    )

    if readme_text != expected_content:
        if fix:
            README.write_text(expected_content)
            print("✅ README.md has been updated with the latest API routes.")
            return 0
        else:
            print("❌ README.md is out of sync with the API routes.")
            print("Run `uv run scripts/check_doc_routes.py --fix` to update it.")
            return 1

    print(
        f"✅ All {len(routes)} API routes are documented and up-to-date in README.md."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Check API routes drift in README.md")
    parser.add_argument("--fix", action="store_true", help="Fix drift in README.md")
    args = parser.parse_args()

    routes = get_app_routes()
    return check_routes_in_readme(routes, fix=args.fix)


if __name__ == "__main__":
    sys.exit(main())
