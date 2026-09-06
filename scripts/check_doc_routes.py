#!/usr/bin/env -S uv run python
"""Drift-prevention check: verify that the API routes table in README.md matches the OpenAPI schema.

Usage (from repo root):
    uv run scripts/check_doc_routes.py [--fix]

The script imports the h4ckath0n app, generates the route table from the OpenAPI schema,
and ensures that the section between <!-- BEGIN API ROUTES --> and <!-- END API ROUTES -->
is exactly up to date.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"

# FastAPI paths omitted from user docs.
FRAMEWORK_PATHS = frozenset(
    {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}
)


def generate_routes_markdown() -> str:
    from h4ckath0n.app import create_app  # noqa: E402
    from h4ckath0n.config import Settings  # noqa: E402

    settings = Settings(
        database_url="sqlite+aiosqlite://",
        password_auth_enabled=True,
    )
    app = create_app(settings)
    openapi = app.openapi()
    paths = openapi.get("paths", {})

    routes_by_tag: dict[str, list[tuple[str, str, str]]] = {}

    for path, path_item in paths.items():
        if path in FRAMEWORK_PATHS:
            continue
        for method, op in path_item.items():
            method_upper = method.upper()
            summary = op.get("summary", "")
            tags = op.get("tags", ["default"])
            tag = tags[0] if tags else "default"
            routes_by_tag.setdefault(tag, []).append((method_upper, path, summary))

    lines = []

    ordered_tags = sorted(routes_by_tag.keys())
    if "default" in ordered_tags:
        ordered_tags.remove("default")
        ordered_tags.insert(0, "default")

    for tag in ordered_tags:
        # Title case except for specific known tags like 'llm'
        tag_title = "LLM" if tag == "llm" else tag.replace("-", " ").title()
        if tag == "default":
            tag_title = "General"

        lines.append(f"### {tag_title}")
        lines.append("")
        for method, path, summary in sorted(
            routes_by_tag[tag], key=lambda x: (x[1], x[0])
        ):
            lines.append(f"- `{method} {path}` — {summary.lower()}.")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fix", action="store_true", help="Update the README automatically"
    )
    args = parser.parse_args()

    generated_md = generate_routes_markdown()
    readme_text = README.read_text(encoding="utf-8")

    start_marker = "<!-- BEGIN API ROUTES -->\n"
    end_marker = "<!-- END API ROUTES -->"

    start_idx = readme_text.find(start_marker)
    end_idx = readme_text.find(end_marker)

    if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
        print(
            "❌ Could not find valid <!-- BEGIN API ROUTES --> and "
            "<!-- END API ROUTES --> markers in README.md."
        )
        return 1

    pre = readme_text[: start_idx + len(start_marker)]
    post = readme_text[end_idx:]

    current_section = readme_text[start_idx + len(start_marker) : end_idx]

    if current_section == generated_md:
        print("✅ API routes in README.md are up to date.")
        return 0

    if args.fix:
        new_readme = pre + generated_md + post
        README.write_text(new_readme, encoding="utf-8")
        print("🔧 Fixed API routes in README.md.")
        return 0
    else:
        print("❌ API routes in README.md are out of date.")
        print("Run `uv run scripts/check_doc_routes.py --fix` to update it.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
