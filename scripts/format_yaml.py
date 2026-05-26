#!/usr/bin/env python3
"""Format YAML files: sort keys, 2-space indent, trailing newline."""

import pathlib
import sys

import yaml


def format_file(path: str) -> bool:
    """
    Format a single YAML file in place.

    Return True if the file was modified.
    """
    with pathlib.Path(path).open() as f:
        original = f.read()

    obj = yaml.safe_load(original)
    formatted = yaml.dump(
        obj,
        sort_keys=True,
        default_flow_style=False,
        allow_unicode=True,
        indent=2,
    )

    if formatted == original:
        return False

    with pathlib.Path(path).open("w") as f:
        _ = f.write(formatted)
    return True


def main() -> int:
    """Entrypoint. Format all files passed as arguments."""
    modified = [path for path in sys.argv[1:] if format_file(path)]

    if modified:
        for path in modified:
            _ = sys.stdout.write(f"reformatted: {path}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
