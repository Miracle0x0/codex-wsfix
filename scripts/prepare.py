#!/usr/bin/env python3
"""Apply reviewed patches to the exact source revision recorded in source.json."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def normalize_release_lockfile(source: Path, expected_digest: str) -> None:
    """Release tags bump workspace.version but leave local lock entries at 0.0.0."""
    workspace = tomllib.loads((source / "codex-rs/Cargo.toml").read_text())["workspace"]
    version = workspace["package"]["version"]
    packages = set()
    # Cargo also includes local path dependencies not listed in workspace.members.
    for path in (source / "codex-rs").rglob("Cargo.toml"):
        if "target" in path.relative_to(source / "codex-rs").parts:
            continue
        package = tomllib.loads(path.read_text()).get("package", {})
        if package.get("version") == {"workspace": True}:
            packages.add(package["name"])
    lock = source / "codex-rs/Cargo.lock"
    blocks = lock.read_text().split("[[package]]")
    for index in range(1, len(blocks)):
        package = tomllib.loads("[[package]]" + blocks[index])["package"][0]
        if "source" not in package and package["name"] in packages:
            if package["version"] not in ("0.0.0", version):
                raise RuntimeError("Unexpected local package version in Cargo.lock")
            blocks[index] = re.sub(
                r'^version = "[^"]+"$', f'version = "{version}"',
                blocks[index], count=1, flags=re.MULTILINE,
            )
    normalized = "[[package]]".join(blocks).encode()
    if hashlib.sha256(normalized).hexdigest() != expected_digest:
        raise RuntimeError("Normalized Cargo.lock differs from the reviewed lockfile")
    lock.write_bytes(normalized)


def prepare(source: Path, config_path: Path = ROOT / "source.json") -> dict:
    config = json.loads(config_path.read_text())
    patches = [ROOT / name for name in config["patches"]]
    for name, expected_digest in config["patches"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected_digest:
            raise RuntimeError(f"Patch checksum mismatch: {name}; review it with source.json")
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=source, text=True
    ).strip()
    if head != config["upstream_sha"]:
        raise RuntimeError(f"Wrong upstream commit: {head}; expected {config['upstream_sha']}")
    dirty = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=no"], cwd=source, text=True
    )
    if dirty:
        raise RuntimeError("Upstream tracked files must be clean before patching")
    untracked_before = set(subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard"], cwd=source, text=True
    ).splitlines())
    subprocess.run(["git", "apply", "--check", *map(str, patches)], cwd=source, check=True)
    normalize_release_lockfile(source, config["normalized_lock_sha256"])
    subprocess.run(["git", "apply", *map(str, patches)], cwd=source, check=True)
    changed = set(subprocess.check_output(
        ["git", "diff", "--name-only"], cwd=source, text=True
    ).splitlines())
    untracked_after = set(subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard"], cwd=source, text=True
    ).splitlines())
    changed.update(untracked_after - untracked_before)
    if changed != {"codex-rs/Cargo.lock", *config["patched_files"]}:
        raise RuntimeError(f"Unexpected modified files: {sorted(changed)}")
    subprocess.run(["git", "diff", "--check"], cwd=source, check=True)
    config["patched_source_sha256"] = {
        name: hashlib.sha256((source / name).read_bytes()).hexdigest()
        for name in config["patched_files"]
    }
    return config


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--metadata", type=Path)
    args = parser.parse_args()
    result = prepare(args.source.resolve())
    if args.metadata:
        args.metadata.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Applied {len(result['patches'])} patches to {result['upstream_tag']} ({result['upstream_sha']})")
