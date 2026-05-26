#!/usr/bin/env python3
"""Format JSON files: sort keys, indent with 2 spaces, trailing newline."""

import json
import pathlib
import sys


def format_file(path: str) -> bool:
    """
    Format a single JSON file in place.

    Return True if the file was modified.
    """
    with pathlib.Path(path).open() as f:
        original = f.read()

    obj = json.loads(original)
    formatted = json.dumps(obj, sort_keys=True, indent=2) + "\n"

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
