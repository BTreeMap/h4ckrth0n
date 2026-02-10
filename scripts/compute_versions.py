from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tomllib
from datetime import UTC, datetime
from pathlib import Path

SEMVER_TAG = re.compile(r"^v(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)$")


def read_pyproject_version(path: Path) -> str:
    data = tomllib.loads(path.read_text())
    return data["project"]["version"]


def read_package_version(path: Path) -> str:
    return json.loads(path.read_text())["version"]


def parse_version(version: str) -> tuple[int, int, int]:
    match = SEMVER_TAG.match(f"v{version}" if not version.startswith("v") else version)
    if not match:
        raise ValueError(f"Invalid version: {version}")
    return int(match["major"]), int(match["minor"]), int(match["patch"])


def format_version(version: tuple[int, int, int]) -> str:
    return f"{version[0]}.{version[1]}.{version[2]}"


def latest_stable_tag() -> tuple[str, tuple[int, int, int]] | None:
    try:
        raw_tags = subprocess.check_output(["git", "tag"], text=True).splitlines()
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("Failed to read git tags") from exc

    stable_tags: list[tuple[tuple[int, int, int], str]] = []
    for tag in raw_tags:
        match = SEMVER_TAG.match(tag)
        if not match:
            continue
        version = (int(match["major"]), int(match["minor"]), int(match["patch"]))
        stable_tags.append((version, tag))

    if not stable_tags:
        return None

    version, tag = max(stable_tags, key=lambda item: item[0])
    return tag, version


def determine_channel(channel: str | None) -> str:
    if channel:
        return channel
    env_channel = os.environ.get("RELEASE_CHANNEL")
    if env_channel:
        return env_channel
    if os.environ.get("GITHUB_REF_TYPE") == "tag":
        return "stable"
    if os.environ.get("GITHUB_EVENT_NAME") == "schedule":
        return "nightly"
    return "dev"


def base_version_from_files(root: Path) -> tuple[int, int, int]:
    pyproject_version = read_pyproject_version(root / "pyproject.toml")
    package_version = read_package_version(root / "packages" / "create-h4ckrth0n" / "package.json")
    if pyproject_version != package_version:
        raise ValueError(
            "pyproject.toml and package.json versions do not match: "
            f"{pyproject_version} vs {package_version}"
        )
    return parse_version(pyproject_version)


def compute_versions(channel: str, root: Path) -> dict[str, str]:
    now = datetime.now(UTC)
    latest_tag = latest_stable_tag()
    tag_ref = os.environ.get("GITHUB_REF_NAME") or os.environ.get("GITHUB_REF", "")
    if "/" in tag_ref:
        tag_ref = tag_ref.rsplit("/", 1)[-1]

    if channel == "stable":
        match = SEMVER_TAG.match(tag_ref)
        if not match:
            raise ValueError(f"Stable release requires a semver tag, got: {tag_ref}")
        version = (
            int(match["major"]),
            int(match["minor"]),
            int(match["patch"]),
        )
        version_str = format_version(version)
        return {
            "npm_version": version_str,
            "pypi_version": version_str,
            "dist_tag": "latest",
            "channel": channel,
            "base_version": version_str,
        }

    if latest_tag:
        base_version = (latest_tag[1][0], latest_tag[1][1], latest_tag[1][2] + 1)
    else:
        base_version = base_version_from_files(root)
        base_version = (base_version[0], base_version[1], base_version[2] + 1)

    base_version_str = format_version(base_version)

    if channel == "nightly":
        npm_version = f"{base_version_str}-dev.{now:%Y-%m-%d}"
        pypi_version = f"{base_version_str}.dev{now:%Y%m%d}"
        dist_tag = "nightly"
    else:
        sha = os.environ.get("GITHUB_SHA")
        if not sha:
            sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        sha7 = sha[:7]
        npm_version = f"{base_version_str}-dev.{now:%Y-%m-%d.%H-%M-%S}.{sha7}"
        pypi_version = f"{base_version_str}.dev{now:%Y%m%d%H%M%S}"
        dist_tag = "dev"

    return {
        "npm_version": npm_version,
        "pypi_version": pypi_version,
        "dist_tag": dist_tag,
        "channel": channel,
        "base_version": base_version_str,
    }


def write_outputs(values: dict[str, str]) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as handle:
            for key, value in values.items():
                handle.write(f"{key}={value}\n")
    print(json.dumps(values, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", choices=["dev", "nightly", "stable"])
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    channel = determine_channel(args.channel)
    values = compute_versions(channel, root)
    write_outputs(values)


if __name__ == "__main__":
    main()
