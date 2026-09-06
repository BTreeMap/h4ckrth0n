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


def get_app_routes() -> list[tuple[str, str, str, str]]:
    """Return (tag, method, path, summary) tuples from the live FastAPI app OpenAPI schema."""
    from h4ckath0n.app import create_app  # noqa: E402
    from h4ckath0n.config import Settings  # noqa: E402

    settings = Settings(
        database_url="sqlite+aiosqlite://",
        password_auth_enabled=True,
    )
    app = create_app(settings)
    schema = app.openapi()

    routes: list[tuple[str, str, str, str]] = []
    for path, path_item in schema.get("paths", {}).items():
        if path in FRAMEWORK_PATHS:
            continue
        for method, operation in path_item.items():
            if method.lower() == "head":
                continue
            tags = operation.get("tags", ["default"])
            primary_tag = tags[0]
            summary = operation.get("summary", "")
            routes.append((primary_tag, method.upper(), path, summary))
    return sorted(routes, key=lambda r: (r[0], r[1], r[2]))


def check_routes_in_readme(
    routes: list[tuple[str, str, str, str]],
) -> list[tuple[str, str]]:
    """Return routes that are not mentioned anywhere in README.md."""
    readme_text = README.read_text()
    missing: list[tuple[str, str]] = []
    for _tag, method, path, _summary in routes:
        path_re = re.escape(path)
        combined = rf"`{method}\s+{path_re}`"
        if not re.search(combined, readme_text, re.IGNORECASE):
            missing.append((method, path))
    return missing


def fix_readme(routes: list[tuple[str, str, str, str]]) -> None:
    """Inject the generated route documentation into README.md."""
    readme_text = README.read_text()

    routes_by_tag: dict[str, list[str]] = {}
    for tag, method, path, summary in routes:
        if tag not in routes_by_tag:
            routes_by_tag[tag] = []
        summary_lower = summary.lower()
        if summary_lower and not summary_lower.endswith("."):
            summary_lower += "."
        routes_by_tag[tag].append(f"- `{method} {path}` — {summary_lower}")

    tag_titles = {
        "default": "",
        "auth": "Session",
        "passkey": "Passkeys",
        "jobs": "Background Jobs",
        "uploads": "Uploads",
        "llm": "LLM Chat",
        "password-auth": "Password Auth",
    }

    markdown: list[str] = []
    if "default" in routes_by_tag:
        markdown.extend(routes_by_tag["default"])

    for tag, items in routes_by_tag.items():
        if tag == "default":
            continue
        markdown.append(f"\n### {tag_titles.get(tag, tag.title())}")
        markdown.extend(items)

    generated_md = "\n".join(markdown)

    pattern = re.compile(
        r"(<!-- BEGIN API ROUTES -->).*?(<!-- END API ROUTES -->)", re.DOTALL
    )
    if not pattern.search(readme_text):
        print(
            "❌ Error: <!-- BEGIN API ROUTES --> and <!-- END API ROUTES --> "
            "markers not found in README.md.",
            file=sys.stderr,
        )
        sys.exit(1)

    new_readme = pattern.sub(rf"\1\n\n{generated_md}\n\n\2", readme_text)
    README.write_text(new_readme)
    print("✅ Successfully updated README.md with dynamically generated routes.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check or fix API route documentation."
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically generate and inject routes into README.md",
    )
    args = parser.parse_args()

    routes = get_app_routes()

    if args.fix:
        fix_readme(routes)
        return 0

    missing = check_routes_in_readme(routes)

    if missing:
        print("❌ The following API routes are NOT documented in README.md:\n")
        for method, path in missing:
            print(f"  {method:6s} {path}")
        print(
            "\nRun `uv run scripts/check_doc_routes.py --fix` to automatically "
            "generate and inject them."
        )
        return 1

    print(f"✅ All {len(routes)} API routes are documented in README.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
