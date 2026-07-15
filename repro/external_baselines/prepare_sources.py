#!/usr/bin/env python3
"""Clone the exact external baseline revisions required by the adapters."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


SOURCES = {
    "A-mem": ("https://github.com/WujiangXu/A-mem.git", "0c8039f28fdcc08189a23c07a3437d9d2482f9c2"),
    "mem0": ("https://github.com/mem0ai/mem0.git", "ccbe5861a138c7583e01bb3a3aa6168e52526a23"),
}


def run(*args: str, cwd: Path | None = None) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="external")
    args = parser.parse_args()
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    for name, (url, commit) in SOURCES.items():
        target = root / name
        if not (target / ".git").exists():
            run("git", "clone", url, str(target))
        run("git", "fetch", "origin", commit, "--depth", "1", cwd=target)
        run("git", "checkout", "--detach", commit, cwd=target)
        actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=target, text=True).strip()
        if actual != commit:
            raise RuntimeError(f"{name}: expected {commit}, got {actual}")
        print(f"{name}: {actual}")


if __name__ == "__main__":
    main()
