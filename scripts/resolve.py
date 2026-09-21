#!/usr/bin/env python3
"""Resolve the pinned source and the selected native GitHub runner matrix."""

import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TARGETS = {
    "linux-x64": ("ubuntu-24.04", "x86_64-unknown-linux-musl"),
    "linux-arm64": ("ubuntu-24.04-arm", "aarch64-unknown-linux-musl"),
    "macos-arm64": ("macos-15", "aarch64-apple-darwin"),
    "macos-x64": ("macos-15-intel", "x86_64-apple-darwin"),
    "windows-x64": ("windows-2022", "x86_64-pc-windows-msvc"),
}


def resolve(selection: str) -> dict:
    config = json.loads((ROOT / "source.json").read_text())
    if not re.fullmatch(r"[0-9a-f]{40}", config["upstream_sha"]):
        raise ValueError("source.json must pin a full Git commit SHA")
    if not re.fullmatch(r"rust-v\d+\.\d+\.\d+", config["upstream_tag"]):
        raise ValueError("Only stable upstream releases are configured")
    if selection == "all":
        names = list(TARGETS)
    elif selection == "linux-and-apple-silicon":
        names = ["linux-x64", "macos-arm64"]
    else:
        names = [selection]
    matrix = {
        "include": [
            {"name": name, "runner": TARGETS[name][0], "target": TARGETS[name][1]}
            for name in names
        ]
    }
    return {
        "sha": config["upstream_sha"],
        "tag": config["upstream_tag"],
        "matrix": json.dumps(matrix, separators=(",", ":")),
        "targets": json.dumps([TARGETS[name][1] for name in names]),
        "version": config["upstream_tag"].removeprefix("rust-v") + f"-keepalive.{config['patch_revision']}",
    }


if __name__ == "__main__":
    outputs = resolve(os.environ.get("SELECTED_TARGETS", "linux-and-apple-silicon"))
    with open(os.environ["GITHUB_OUTPUT"], "a") as output:
        for key, value in outputs.items():
            output.write(f"{key}={value}\n")
