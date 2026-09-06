#!/usr/bin/env -S uv run python
"""Drift-prevention check: verify that every API route in the FastAPI app is documented.

Usage (from repo root):
    uv run scripts/check_doc_routes.py

The script imports the h4ckath0n app, enumerates all routes, and checks that
README.md mentions each one. Routes provided by FastAPI itself (e.g. /openapi.json,
/docs, /redoc) are excluded from the check.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"

# FastAPI paths omitted from user docs.
FRAMEWORK_PATHS = frozenset(
    {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}
)


def get_app_routes() -> list[tuple[str, str, str]]:
    """Return (method, path, summary) pairs from the live FastAPI app's OpenAPI schema."""
    from h4ckath0n.app import create_app  # noqa: E402
    from h4ckath0n.config import Settings  # noqa: E402

    settings = Settings(
        database_url="sqlite+aiosqlite://",
        password_auth_enabled=True,
    )
    app = create_app(settings)

    openapi_schema = app.openapi()
    paths = openapi_schema.get("paths", {})
    routes: list[tuple[str, str, str]] = []

    for path, methods_dict in paths.items():
        if path in FRAMEWORK_PATHS:
            continue
        for method, op in methods_dict.items():
            if method.upper() == "HEAD":
                continue
            summary = op.get("summary", "")
            if summary:
                summary = summary[0].lower() + summary[1:]
            routes.append((method.upper(), path, summary))

    return sorted(routes)


def generate_routes_block(routes: list[tuple[str, str, str]]) -> str:
    """Generate the markdown block for API routes."""
    lines = ["<!-- BEGIN API ROUTES -->"]
    for method, path, summary in routes:
        suffix = f" — {summary}" if summary else ""
        lines.append(f"- `{method} {path}`{suffix}")
    lines.append("<!-- END API ROUTES -->")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check or fix API routes documentation."
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Fix README.md by updating the API routes block.",
    )
    args = parser.parse_args()

    routes = get_app_routes()
    expected_block = generate_routes_block(routes)

    readme_text = README.read_text()

    start_marker = "<!-- BEGIN API ROUTES -->"
    end_marker = "<!-- END API ROUTES -->"

    if start_marker not in readme_text or end_marker not in readme_text:
        print(f"❌ Missing {start_marker} or {end_marker} in README.md")
        return 1

    pattern = re.compile(rf"{start_marker}.*?{end_marker}", re.DOTALL)
    current_block_match = pattern.search(readme_text)

    if not current_block_match:
        print("❌ Could not extract the current API routes block from README.md")
        return 1

    if current_block_match.group(0) == expected_block:
        print(f"✅ All {len(routes)} API routes are correctly documented in README.md.")
        return 0

    if args.fix:
        new_readme_text = pattern.sub(expected_block, readme_text)
        README.write_text(new_readme_text)
        print(f"✨ Updated README.md with {len(routes)} API routes.")
        return 0

    print("❌ The API routes in README.md do not match the expected output.")
    print("Run `uv run scripts/check_doc_routes.py --fix` to update it.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
