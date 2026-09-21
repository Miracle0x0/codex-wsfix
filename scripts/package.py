#!/usr/bin/env python3
"""Use upstream's canonical package layout, then add provenance and licenses."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(os.environ["CODEX_REPO_ROOT"])
sys.path.insert(0, str(ROOT / "scripts"))
from codex_package.archive import write_archive

target = os.environ["TARGET"]
version = os.environ["PACKAGE_VERSION"]
suffix = ".exe" if "windows" in target else ""
release = ROOT / "codex-rs/target" / target / "release"
package = ROOT / "package"
dist = ROOT / "dist"
dist.mkdir(exist_ok=True)
args = [
    sys.executable, str(ROOT / "scripts/build_codex_package.py"),
    "--target", target, "--package-version", version,
    "--package-dir", str(package),
    "--entrypoint-bin", str(release / f"codex{suffix}"),
    "--code-mode-host-bin", str(release / f"codex-code-mode-host{suffix}"),
]
if "linux" in target:
    args += ["--bwrap-bin", str(release / "bwrap")]
if suffix:
    args += [
        "--codex-command-runner-bin", str(release / "codex-command-runner.exe"),
        "--codex-windows-sandbox-setup-bin", str(release / "codex-windows-sandbox-setup.exe"),
    ]
subprocess.run(args, check=True)
for name in ("LICENSE", "NOTICE"):
    if (ROOT / name).is_file():
        shutil.copy2(ROOT / name, package / name)
metadata = json.loads((ROOT / "patch-metadata.json").read_text())
for name in metadata["patches"]:
    shutil.copy2(ROOT / ".keepalive-ci" / name, package / Path(name).name)
metadata.update({
    "target": target, "package_version": version,
    "builder_sha": os.environ.get("BUILDER_SHA"),
    "run_url": os.environ.get("BUILD_RUN_URL"),
    "rustc": subprocess.check_output(["rustc", "--version"], text=True).strip(),
    "signed": False, "native_voice_runtime_included": False,
})
(package / "BUILD-INFO.json").write_text(json.dumps(metadata, indent=2) + "\n")
subprocess.run([str(package / f"bin/codex{suffix}"), "--version"], check=True)
subprocess.run([str(package / f"bin/codex{suffix}"), "--help"], check=True, stdout=subprocess.DEVNULL)
extension = ".zip" if suffix else ".tar.gz"
archive = dist / f"codex-{version}-{target}{extension}"
write_archive(package, archive, force=False)
with archive.open("rb") as content:
    digest = hashlib.file_digest(content, "sha256").hexdigest()
(dist / (archive.name + ".sha256")).write_text(f"{digest}  {archive.name}\n")
shutil.copy2(package / "BUILD-INFO.json", dist / f"build-info-{target}.json")
print(f"Packaged and smoke-tested {archive.name}")
