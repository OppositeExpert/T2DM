#!/usr/bin/env python3
"""Verify the active interpreter and installed distributions against the lock."""

from __future__ import annotations

from importlib import metadata
from pathlib import Path
import platform
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "requirements.lock"
PIN = re.compile(r"^([A-Za-z0-9_.-]+)==([^;\s]+)$")


def normalized(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def main() -> None:
    if sys.version_info[:2] != (3, 12):
        raise SystemExit(
            f"Unsupported interpreter {platform.python_version()}; use CPython 3.12.x"
        )
    expected: dict[str, tuple[str, str]] = {}
    for line in LOCK.read_text(encoding="utf-8").splitlines():
        match = PIN.match(line.strip())
        if match:
            expected[normalized(match.group(1))] = (match.group(1), match.group(2))
    installed = {
        normalized(distribution.metadata["Name"]): distribution.version
        for distribution in metadata.distributions()
        if distribution.metadata.get("Name")
    }
    failures = []
    for key, (name, version) in expected.items():
        actual = installed.get(key)
        if actual != version:
            failures.append(f"{name}: expected {version}, installed {actual}")
    if failures:
        print("Environment mismatch:")
        print("\n".join(f"- {failure}" for failure in failures))
        raise SystemExit(1)
    print(
        f"Environment OK: Python {platform.python_version()}, "
        f"{len(expected)} locked distributions, platform={platform.platform()}"
    )


if __name__ == "__main__":
    main()
