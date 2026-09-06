#!/usr/bin/env -S uv run python
"""Drift-prevention check: verify that the API routes section in README.md matches the app.

Usage (from repo root):
    uv run scripts/check_doc_routes.py

The script imports the h4ckath0n app, extracts routes via OpenAPI, and verifies
that the exact generated markdown block is present in README.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"


def get_routes_markdown() -> str:
    from h4ckath0n.app import create_app
    from h4ckath0n.config import Settings

    settings = Settings(database_url="sqlite+aiosqlite://", password_auth_enabled=True)
    app = create_app(settings)
    paths = app.openapi().get("paths", {})

    lines = []
    lines.append("<!-- BEGIN ROUTES -->")

    routes_by_tag: dict[str, list[tuple[str, str, str]]] = {}
    for path, methods in paths.items():
        for method, op in methods.items():
            tags = op.get("tags", ["default"])
            tag = tags[0] if tags else "default"
            if tag not in routes_by_tag:
                routes_by_tag[tag] = []

            summary = op.get("summary", "")
            routes_by_tag[tag].append((method.upper(), path, summary))

    for tag in sorted(routes_by_tag.keys()):
        if tag == "default":
            lines.append("### General")
        else:
            lines.append(f"### {tag.title()}")

        for method, path, summary in sorted(routes_by_tag[tag], key=lambda x: x[1]):
            # Match exact format for markdown list
            lines.append(f"- `{method} {path}` — {summary}")

    lines.append("<!-- END ROUTES -->")
    return "\n".join(lines)


def main() -> int:
    expected = get_routes_markdown()
    readme_text = README.read_text()

    if expected not in readme_text:
        print("❌ The API routes section in README.md is out of date.")
        print("\nPlease update README.md to contain exactly the following block:\n")
        print(expected)
        return 1

    print("✅ API routes in README.md are up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
