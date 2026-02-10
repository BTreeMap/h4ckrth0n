from __future__ import annotations

import argparse
import json
import re
import tomllib
from pathlib import Path


def read_pyproject_version(path: Path) -> str:
    data = tomllib.loads(path.read_text())
    return data["project"]["version"]


def read_package_version(path: Path) -> str:
    return json.loads(path.read_text())["version"]


def update_pyproject_version(path: Path, version: str) -> None:
    content = path.read_text()
    updated, count = re.subn(
        r'^version = ".*"$', f'version = "{version}"', content, count=1, flags=re.M
    )
    if count != 1:
        raise ValueError(f"Failed to update version in {path}")
    path.write_text(updated)


def update_package_json_version(path: Path, version: str) -> None:
    data = json.loads(path.read_text())
    data["version"] = version
    path.write_text(json.dumps(data, indent=2) + "\n")


def update_package_lock_version(path: Path, version: str) -> None:
    if not path.exists():
        return
    data = json.loads(path.read_text())
    data["version"] = version
    packages = data.get("packages")
    if isinstance(packages, dict) and "" in packages:
        packages[""]["version"] = version
    path.write_text(json.dumps(data, indent=2) + "\n")


def validate_versions(pyproject_path: Path, package_json_path: Path, version: str) -> None:
    pyproject_version = read_pyproject_version(pyproject_path)
    package_version = read_package_version(package_json_path)
    if pyproject_version != version or package_version != version:
        raise ValueError(
            "Stable release requires versions to match tag: "
            f"pyproject={pyproject_version}, package.json={package_version}, tag={version}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--npm-version", required=True)
    parser.add_argument("--pypi-version", required=True)
    parser.add_argument("--channel", choices=["dev", "nightly", "stable"], required=True)
    parser.add_argument("--root", default=None)
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[1]
    pyproject_path = root / "pyproject.toml"
    package_dir = root / "packages" / "create-h4ckath0n"
    package_json_path = package_dir / "package.json"
    package_lock_path = package_dir / "package-lock.json"

    if args.channel == "stable":
        validate_versions(pyproject_path, package_json_path, args.pypi_version)
        return

    update_pyproject_version(pyproject_path, args.pypi_version)
    update_package_json_version(package_json_path, args.npm_version)
    update_package_lock_version(package_lock_path, args.npm_version)


if __name__ == "__main__":
    main()
