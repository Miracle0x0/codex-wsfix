import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prepare = load_script("prepare")
release = load_script("release")
resolve = load_script("resolve")


class PatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.file = self.source / prepare.SOURCE_FILE
        self.file.parent.mkdir(parents=True)
        self.file.write_text("before\n")
        (self.source / "codex-rs/Cargo.toml").write_text(
            '[workspace]\nmembers = ["fixture"]\n[workspace.package]\nversion = "0.155.1"\n'
        )
        member = self.source / "codex-rs/fixture"
        member.mkdir()
        (member / "Cargo.toml").write_text('[package]\nname = "fixture"\nversion.workspace = true\n')
        local_package = '[[package]]\nname = "fixture"\nversion = "0.0.0"\n'
        external_package = (
            '\n[[package]]\nname = "external"\nversion = "0.0.0"\n'
            'source = "registry+https://example.invalid/index"\n'
        )
        (self.source / "codex-rs/Cargo.lock").write_text(local_package + external_package)
        normalized_lock = local_package.replace('"0.0.0"', '"0.155.1"') + external_package
        for command in (["init", "-q"], ["add", "."], [
            "-c", "user.name=CI Test", "-c", "user.email=test@example.invalid",
            "commit", "-qm", "fixture",
        ]):
            subprocess.run(["git", *command], cwd=self.source, check=True)
        self.sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=self.source, text=True
        ).strip()
        (self.root / "patches").mkdir()
        self.patch = self.root / "patches/keepalive.patch"
        self.patch.write_text(
            f"--- a/{prepare.SOURCE_FILE}\n+++ b/{prepare.SOURCE_FILE}\n"
            "@@ -1 +1 @@\n-before\n+after\n"
        )
        self.config = self.root / "source.json"
        self.config.write_text(json.dumps({
            "upstream_sha": self.sha, "upstream_tag": "rust-v0.155.1",
            "patch_sha256": hashlib.sha256(self.patch.read_bytes()).hexdigest(),
            "normalized_lock_sha256": hashlib.sha256(normalized_lock.encode()).hexdigest(),
        }))
        self.root_patch = patch.object(prepare, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def test_applies_only_to_clean_pinned_source_and_rejects_repeat(self):
        result = prepare.prepare(self.source, self.config)
        self.assertEqual(self.file.read_text(), "after\n")
        self.assertEqual(result["upstream_sha"], self.sha)
        self.assertIn('name = "external"\nversion = "0.0.0"',
                      (self.source / "codex-rs/Cargo.lock").read_text())
        with self.assertRaisesRegex(RuntimeError, "must be clean"):
            prepare.prepare(self.source, self.config)

    def test_rejects_tampered_patch_before_writing(self):
        self.patch.write_text(self.patch.read_text() + "tampered\n")
        with self.assertRaisesRegex(RuntimeError, "checksum mismatch"):
            prepare.prepare(self.source, self.config)
        self.assertEqual(self.file.read_text(), "before\n")

    def test_rejects_wrong_source_before_writing(self):
        config = json.loads(self.config.read_text())
        config["upstream_sha"] = "0" * 40
        self.config.write_text(json.dumps(config))
        with self.assertRaisesRegex(RuntimeError, "Wrong upstream commit"):
            prepare.prepare(self.source, self.config)
        self.assertEqual(self.file.read_text(), "before\n")


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dist = Path(self.temp.name)
        self.target = "x86_64-unknown-linux-musl"
        self.version = "0.155.1-keepalive.1"
        self.archive = self.dist / f"codex-{self.version}-{self.target}.tar.gz"
        self.archive.write_bytes(b"archive fixture")
        digest = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        (self.dist / (self.archive.name + ".sha256")).write_text(f"{digest}  {self.archive.name}\n")
        (self.dist / f"build-info-{self.target}.json").write_text(json.dumps({
            "target": self.target, "package_version": self.version,
        }))

    def test_complete_artifacts_pass(self):
        self.assertEqual(len(release.verify_assets(self.dist, [self.target], self.version)), 3)

    def test_corrupt_archive_cannot_publish(self):
        self.archive.write_bytes(b"corrupt")
        with self.assertRaisesRegex(RuntimeError, "Checksum mismatch"):
            release.verify_assets(self.dist, [self.target], self.version)

    def test_missing_matrix_target_cannot_publish(self):
        with self.assertRaisesRegex(RuntimeError, "Incomplete"):
            release.verify_assets(self.dist, [self.target, "aarch64-apple-darwin"], self.version)

    def test_extra_asset_cannot_publish(self):
        (self.dist / "unexpected.bin").write_bytes(b"unexpected")
        with self.assertRaisesRegex(RuntimeError, "Unexpected"):
            release.verify_assets(self.dist, [self.target], self.version)


class MatrixTests(unittest.TestCase):
    def test_all_and_single_platform_selection(self):
        for selection in ["all", "linux-and-apple-silicon", *resolve.TARGETS]:
            result = resolve.resolve(selection)
            targets = json.loads(result["targets"])
            matrix = json.loads(result["matrix"])["include"]
            self.assertEqual([entry["target"] for entry in matrix], targets)
            self.assertEqual(len(targets), {"all": 5, "linux-and-apple-silicon": 2}.get(selection, 1))


if __name__ == "__main__":
    unittest.main()
