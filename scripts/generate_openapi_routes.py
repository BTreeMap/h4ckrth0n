#!/usr/bin/env -S uv run python
"""Drift-prevention script to auto-generate the documented routes in README.md from OpenAPI spec."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"

FRAMEWORK_PATHS = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}


def generate_routes_markdown() -> str:
    from h4ckath0n.app import create_app
    from h4ckath0n.config import Settings

    settings = Settings(
        database_url="sqlite+aiosqlite://",
        password_auth_enabled=True,
    )
    app = create_app(settings)
    openapi = app.openapi()
    paths = openapi.get("paths", {})

    tags_to_routes: dict[str, list[str]] = {}

    for path, path_item in paths.items():
        if path in FRAMEWORK_PATHS:
            continue
        for method, op in path_item.items():
            if method.lower() == "head":
                continue
            tags = op.get("tags", [])
            tag = tags[0] if tags else "Other"
            summary = op.get("summary", "").lower()
            if "health" in summary or "welcome" in summary:
                tag = "Other"
            if tag not in tags_to_routes:
                tags_to_routes[tag] = []
            tags_to_routes[tag].append(f"- `{method.upper()} {path}` — {summary}")

    md = "<!-- BEGIN ROUTES -->\n"

    titles = {
        "Other": "General",
        "auth": "Session",
        "jobs": "Background Jobs",
        "uploads": "Uploads",
        "llm": "LLM Chat",
        "passkey": "Passkeys",
        "password-auth": "Password Auth"
    }
    for tag in ["Other", "auth", "jobs", "uploads", "llm", "passkey", "password-auth"]:
        if tag not in tags_to_routes:
            continue
        title = titles.get(tag, tag.capitalize())

        md += f"\n### {title}\n"
        for line in tags_to_routes[tag]:
            md += f"{line}\n"

    md += "<!-- END ROUTES -->"
    return md


def main() -> int:
    readme_text = README.read_text()
    new_routes_md = generate_routes_markdown()

    # Replace the existing routes section with the generated one
    pattern = re.compile(r"<!-- BEGIN ROUTES -->.*<!-- END ROUTES -->", re.DOTALL)

    if "<!-- BEGIN ROUTES -->" in readme_text:
        new_readme_text = pattern.sub(new_routes_md, readme_text)
    else:
        print("Error: Could not find <!-- BEGIN ROUTES --> in README.md")
        return 1

    if readme_text != new_readme_text:
        README.write_text(new_readme_text)
        print("✅ Updated API routes in README.md")
    else:
        print("✅ API routes in README.md are already up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
