#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from difflib import unified_diff
from pathlib import Path

SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(2)


def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def write_text(p: Path, s: str) -> None:
    p.write_text(s, encoding="utf-8")


def parse_pyproject_version(pyproject: Path) -> str:
    s = read_text(pyproject).splitlines()
    in_project = False
    for line in s:
        m = re.match(r"^\s*\[([^\]]+)\]\s*$", line)
        if m:
            in_project = m.group(1).strip() == "project"
            continue
        if in_project:
            vm = re.match(r'^\s*version\s*=\s*"([^"]+)"\s*$', line)
            if vm:
                return vm.group(1)
    die(f"Could not find [project].version in {pyproject}")
    return ""


def bump_semver(old: str, bump: str) -> str:
    m = SEMVER_RE.match(old)
    if not m:
        die(f"Current version is not X.Y.Z semver: {old}")
    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if bump == "patch":
        patch += 1
    elif bump == "minor":
        minor += 1
        patch = 0
    elif bump == "major":
        major += 1
        minor = 0
        patch = 0
    else:
        die(f"Unknown bump: {bump}")
    return f"{major}.{minor}.{patch}"


@dataclass(frozen=True)
class Change:
    path: Path
    before: str
    after: str


def show_diff(ch: Change) -> str:
    return "".join(
        unified_diff(
            ch.before.splitlines(keepends=True),
            ch.after.splitlines(keepends=True),
            fromfile=str(ch.path),
            tofile=str(ch.path),
        )
    )


def replace_project_version_in_pyproject(
    path: Path, old: str, new: str
) -> Change | None:
    before = read_text(path)
    lines = before.splitlines(keepends=True)

    out: list[str] = []
    in_project = False
    changed = False
    for line in lines:
        m = re.match(r"^\s*\[([^\]]+)\]\s*$", line.strip())
        if m:
            in_project = m.group(1).strip() == "project"
            out.append(line)
            continue

        if in_project:
            vm = re.match(r'^(\s*version\s*=\s*")([^"]+)(".*)\n?$', line)
            if vm and vm.group(2) == old:
                out.append(f"{vm.group(1)}{new}{vm.group(3)}\n")
                changed = True
                continue

        out.append(line)

    after = "".join(out)
    if not changed:
        return None
    return Change(path, before, after)


def replace_fallback_version_in_version_py(
    path: Path, old: str, new: str
) -> Change | None:
    before = read_text(path)
    after = re.sub(
        rf'(^\s*__fallback_version__\s*=\s*")({re.escape(old)})(")',
        rf"\g<1>{new}\3",
        before,
        flags=re.MULTILINE,
    )
    if after == before:
        return None
    return Change(path, before, after)


def replace_uv_lock_editable_package_version(
    path: Path, old: str, new: str
) -> Change | None:
    before = read_text(path)

    # Find the [[package]] block for name="h4ckath0n" with source editable="."
    # and replace only its version line.
    pkg_re = re.compile(
        r"(\[\[package\]\]\s*\n"
        r'name\s*=\s*"h4ckath0n"\s*\n'
        r'version\s*=\s*")' + re.escape(old) + r'(".*?\n'
        r'.*?source\s*=\s*\{\s*editable\s*=\s*"\."\s*\}.*?\n'
        r")",
        flags=re.DOTALL,
    )

    m = pkg_re.search(before)
    if not m:
        return None

    after = before[: m.start(1)] + m.group(1) + new + m.group(2) + before[m.end(2) :]
    return Change(path, before, after)


def update_package_json_version(path: Path, old: str, new: str) -> Change | None:
    before = read_text(path)
    data = json.loads(before)
    if data.get("version") != old:
        return None
    data["version"] = new
    after = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    return Change(path, before, after)


def update_package_lock_version(path: Path, old: str, new: str) -> Change | None:
    before = read_text(path)
    data = json.loads(before)

    changed = False
    if data.get("version") == old:
        data["version"] = new
        changed = True

    pkgs = data.get("packages")
    if isinstance(pkgs, dict):
        root = pkgs.get("")
        if isinstance(root, dict) and root.get("version") == old:
            root["version"] = new
            changed = True

    if not changed:
        return None

    after = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    return Change(path, before, after)


def update_template_dependency_floor(path: Path, old: str, new: str) -> Change | None:
    before = read_text(path)
    # Replace only the dependency string h4ckath0n>=X.Y.Z inside quotes.
    after = re.sub(
        rf'("h4ckath0n>=){re.escape(old)}(")',
        rf"\g<1>{new}\2",
        before,
    )
    if after == before:
        return None
    return Change(path, before, after)


def update_openapi_info_version(path: Path, old: str, new: str) -> Change | None:
    before = read_text(path)
    data = json.loads(before)
    info = data.get("info")
    if not isinstance(info, dict):
        return None
    if info.get("version") != old:
        return None
    info["version"] = new
    after = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    return Change(path, before, after)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", help="Set explicit new version, e.g. 0.1.2")
    ap.add_argument(
        "--bump", choices=["patch", "minor", "major"], help="Bump semver component"
    )
    ap.add_argument("--apply", action="store_true", help="Write changes to disk")
    args = ap.parse_args(argv)

    if not args.to and not args.bump:
        die("Provide either --to X.Y.Z or --bump {patch,minor,major}")

    pyproject = Path("pyproject.toml")
    old = parse_pyproject_version(pyproject)

    new = args.to if args.to else bump_semver(old, args.bump)
    if not SEMVER_RE.match(new):
        die(f"New version must be X.Y.Z semver: {new}")

    targets = [
        ("pyproject", Path("pyproject.toml"), replace_project_version_in_pyproject),
        ("uv_lock", Path("uv.lock"), replace_uv_lock_editable_package_version),
        (
            "version_py",
            Path("src/h4ckath0n/version.py"),
            replace_fallback_version_in_version_py,
        ),
        (
            "npm_pkg",
            Path("packages/create-h4ckath0n/package.json"),
            update_package_json_version,
        ),
        (
            "npm_lock",
            Path("packages/create-h4ckath0n/package-lock.json"),
            update_package_lock_version,
        ),
        (
            "template_api_pyproject",
            Path("packages/create-h4ckath0n/templates/fullstack/api/pyproject.toml"),
            update_template_dependency_floor,
        ),
        (
            "template_openapi",
            Path("packages/create-h4ckath0n/templates/fullstack/api/openapi.json"),
            update_openapi_info_version,
        ),
    ]

    changes: list[Change] = []
    for _name, path, fn in targets:
        if not path.exists():
            continue
        ch = fn(path, old, new)
        if ch is not None:
            changes.append(ch)

    if not changes:
        die("No changes detected. Did the version already change or files move?")

    for ch in changes:
        sys.stdout.write(show_diff(ch))

    if args.apply:
        for ch in changes:
            write_text(ch.path, ch.after)
        print(f"Applied version bump: {old} -> {new}")
    else:
        print(f"Dry run only. Proposed version bump: {old} -> {new}")
        print("Re-run with --apply to write changes.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
