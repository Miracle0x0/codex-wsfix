#!/usr/bin/env python3
"""Apply a reviewed patch to the exact source revision recorded in source.json."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tomllib

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILE = "codex-rs/codex-api/src/endpoint/responses_websocket.rs"


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
    patch = ROOT / "patches/keepalive.patch"
    digest = hashlib.sha256(patch.read_bytes()).hexdigest()
    if digest != config["patch_sha256"]:
        raise RuntimeError("Patch checksum mismatch; review the patch and source.json together")
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
    subprocess.run(["git", "apply", "--check", str(patch)], cwd=source, check=True)
    normalize_release_lockfile(source, config["normalized_lock_sha256"])
    subprocess.run(["git", "apply", str(patch)], cwd=source, check=True)
    changed = subprocess.check_output(
        ["git", "diff", "--name-only"], cwd=source, text=True
    ).splitlines()
    if changed != ["codex-rs/Cargo.lock", SOURCE_FILE]:
        raise RuntimeError(f"Unexpected modified files: {changed}")
    subprocess.run(["git", "diff", "--check"], cwd=source, check=True)
    config["patched_source_sha256"] = hashlib.sha256(
        (source / SOURCE_FILE).read_bytes()
    ).hexdigest()
    return config


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--metadata", type=Path)
    args = parser.parse_args()
    result = prepare(args.source.resolve())
    if args.metadata:
        args.metadata.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Applied keepalive patch to {result['upstream_tag']} ({result['upstream_sha']})")
