#!/usr/bin/env -S uv run python
"""Drift-prevention check: verify that every API route in the FastAPI app is documented.

Usage (from repo root):
    uv run scripts/check_doc_routes.py [--fix]

The script imports the h4ckath0n app, enumerates all routes, and checks that
README.md mentions each one in the API routes section. Routes provided by FastAPI itself
are excluded from the check.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"

# FastAPI paths omitted from user docs.
FRAMEWORK_PATHS = frozenset(
    {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}
)

ROUTES_SECTION_RE = re.compile(
    r"(<!-- BEGIN ROUTES -->\n)(.*?)(<!-- END ROUTES -->)", re.DOTALL
)


def generate_routes_markdown() -> str:
    """Return the generated markdown for API routes."""
    from h4ckath0n.app import create_app  # noqa: E402
    from h4ckath0n.config import Settings  # noqa: E402

    settings = Settings(
        database_url="sqlite+aiosqlite://",
        password_auth_enabled=True,
    )
    app = create_app(settings)
    openapi = app.openapi()

    routes_by_tag = defaultdict(list)
    for path, path_item in openapi.get("paths", {}).items():
        if path in FRAMEWORK_PATHS:
            continue
        for method, op in path_item.items():
            tags = op.get("tags", ["default"])
            tag = tags[0] if tags else "default"
            routes_by_tag[tag].append((method.upper(), path, op.get("summary", "")))

    lines = []
    for tag, routes in sorted(routes_by_tag.items()):
        lines.append(f"### {tag.title()}")
        for method, path, summary in routes:
            lines.append(f"- `{method} {path}` — {summary}")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true", help="Fix the README.md file")
    args = parser.parse_args()

    readme_text = README.read_text()
    if not ROUTES_SECTION_RE.search(readme_text):
        print(
            "❌ Could not find <!-- BEGIN ROUTES --> and <!-- END ROUTES --> in README.md."
        )
        return 1

    generated_md = generate_routes_markdown()

    match = ROUTES_SECTION_RE.search(readme_text)
    current_md = match.group(2) if match else ""

    if current_md != generated_md:
        if args.fix:
            new_text = ROUTES_SECTION_RE.sub(rf"\g<1>{generated_md}\g<3>", readme_text)
            README.write_text(new_text)
            print("✅ Updated API routes in README.md.")
            return 0
        else:
            print("❌ API routes in README.md are out of date.")
            print("Run `uv run scripts/check_doc_routes.py --fix` to update.")
            return 1

    print("✅ API routes in README.md are up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
