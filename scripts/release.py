#!/usr/bin/env python3
"""Bump version in source and pyproject.toml, commit, and tag."""

import pathlib
import re
import subprocess
import sys

import lumberjack

VERSION_FILE = pathlib.Path(lumberjack.__file__)
"""
`__version__` found at library's root `__init__.py`.
"""
PYPROJECT_FILE = pathlib.Path("pyproject.toml")
LOCKFILE = pathlib.Path("uv.lock")
DUNDER_VERSION_PATTERN = re.compile(r'__version__\s*=\s*"[^"]+"')
"""
`__version__`
"""
PYPROJECT_VERSION_PATTERN = re.compile(r'^version\s*=\s*"[^"]+"', re.MULTILINE)
"""
version key on `pyproject.toml`
"""
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
EXPECTED_ARGC = 2


def update_file(path: pathlib.Path, pattern: re.Pattern[str], replacement: str) -> None:
    """Replace the first match of pattern in file with replacement."""
    content = path.read_text()
    updated = pattern.sub(replacement, content, count=1)

    if updated == content:
        _ = sys.stdout.write(f"error: pattern not found in {path}\n")
        raise SystemExit(1)

    _ = path.write_text(updated)
    _ = sys.stdout.write(f"updated: {path}\n")


def run(args: list[str]) -> None:
    """Run a subprocess, exit on failure."""
    _ = subprocess.run(args, check=True)  # noqa: S603


def main() -> int:
    """Entrypoint. Bump version, commit, and tag."""
    if len(sys.argv) != EXPECTED_ARGC:
        script_name, *_ = sys.argv
        _ = sys.stdout.write(f"usage: {script_name} <version>\n")
        _ = sys.stdout.write(f"example: {script_name} 1.0.0\n")
        return 1

    version = sys.argv[1]

    if not SEMVER_PATTERN.match(version):
        _ = sys.stdout.write(f"error: invalid semver: {version}\n")
        return 1

    update_file(VERSION_FILE, DUNDER_VERSION_PATTERN, f'__version__ = "{version}"')
    update_file(PYPROJECT_FILE, PYPROJECT_VERSION_PATTERN, f'version = "{version}"')

    run(["uv", "lock"])
    run(["uv", "run", "taplo", "format", f"{PYPROJECT_FILE}"])
    run(["git", "add", f"{VERSION_FILE}", f"{PYPROJECT_FILE}", f"{LOCKFILE}"])
    run(["git", "commit", "-m", f"build: {version}"])
    run(["git", "tag", "-a", f"v{version}", "-m", f"Release {version}"])

    _ = sys.stdout.write(f"\ntagged v{version}\n")
    _ = sys.stdout.write("run: git push\n")
    _ = sys.stdout.write("run: git push --tags\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
