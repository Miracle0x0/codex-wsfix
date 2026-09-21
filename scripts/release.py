#!/usr/bin/env python3
"""Verify every selected artifact before creating and publishing a draft release."""

import hashlib
import json
import os
from pathlib import Path
import subprocess


def verify_assets(dist: Path, targets: list[str], version: str) -> list[Path]:
    expected = set()
    for target in targets:
        extension = ".zip" if "windows" in target else ".tar.gz"
        archive_name = f"codex-{version}-{target}{extension}"
        archive = dist / archive_name
        checksum = dist / (archive_name + ".sha256")
        metadata = dist / f"build-info-{target}.json"
        if not all(path.is_file() for path in (archive, checksum, metadata)):
            raise RuntimeError(f"Incomplete build artifacts for {target}")
        with archive.open("rb") as content:
            digest = hashlib.file_digest(content, "sha256").hexdigest()
        if checksum.read_text() != f"{digest}  {archive_name}\n":
            raise RuntimeError(f"Checksum mismatch for {target}")
        info = json.loads(metadata.read_text())
        if info["target"] != target or info["package_version"] != version:
            raise RuntimeError(f"Wrong build metadata for {target}")
        expected.update([archive_name, checksum.name, metadata.name])
    if {path.name for path in dist.iterdir()} != expected:
        raise RuntimeError("Unexpected release artifacts")
    return sorted(dist.iterdir())


if __name__ == "__main__":
    version = os.environ["PACKAGE_VERSION"]
    targets = json.loads(os.environ["EXPECTED_TARGETS"])
    assets = verify_assets(Path("dist"), targets, version)
    tag = f"codex-v{version}-build.{os.environ['GITHUB_RUN_ID']}.{os.environ['GITHUB_RUN_ATTEMPT']}"
    info = json.loads(Path(f"dist/build-info-{targets[0]}.json").read_text())
    checksums = Path("dist/SHA256SUMS")
    checksums.write_text("".join(path.read_text() for path in assets if path.suffix == ".sha256"))
    assets.append(checksums)
    notes = Path("release-notes.md")
    notes.write_text(
        f"Unofficial Codex {version} with 30-second Responses WebSocket keepalive pings.\n\n"
        f"Upstream: `{info['upstream_tag']}` / `{info['upstream_sha']}`\n\n"
        f"Original fix: {info['original_commit_url']}\n\n"
        f"Patch SHA-256: `{info['patch_sha256']}`\n\n"
        f"Build: {info['run_url']}\n\n"
        "The codex-api test suite, keepalive regression, and packaged CLI smoke checks must pass before publication.\n\n"
        "Extract the entire archive and run `bin/codex` (`bin/codex.exe` on Windows). "
        "Keep `codex-resources`, `codex-path`, and `codex-package.json` alongside `bin`. "
        "Do not copy only the executable.\n\n"
        "Binaries are not publisher-signed or notarized. Native voice runtime is not included. "
        "This does not replace the Codex desktop app or guarantee a fix for every reconnect cause.\n"
    )
    subprocess.run([
        "gh", "release", "create", tag, "--repo", os.environ["GITHUB_REPOSITORY"],
        "--target", os.environ["GITHUB_SHA"], "--title", f"Codex {version}",
        "--notes-file", str(notes), "--draft", *map(str, assets),
    ], check=True)
    subprocess.run([
        "gh", "release", "edit", tag, "--repo", os.environ["GITHUB_REPOSITORY"],
        "--draft=false", "--latest=false",
    ], check=True)
    print(f"Published {tag}")
