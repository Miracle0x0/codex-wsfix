#!/usr/bin/env bash
set -euo pipefail
: "${TARGET:?}"
: "${PACKAGE_VERSION:?}"
: "${CODEX_REPO_ROOT:?}"
cd "$CODEX_REPO_ROOT/codex-rs"
export STABLE_GIT_COMMIT
STABLE_GIT_COMMIT="$(git rev-parse HEAD)"
args=(--locked --release --target "$TARGET")
binaries=(--bin codex --bin codex-code-mode-host)
case "$TARGET" in
  *-linux-musl)
    cargo build "${args[@]}" --bin bwrap
    strip --strip-debug --strip-unneeded "target/$TARGET/release/bwrap"
    CODEX_BWRAP_SHA256="$(sha256sum "target/$TARGET/release/bwrap" | cut -d ' ' -f 1)"
    export CODEX_BWRAP_SHA256
    ;;
  *-windows-msvc)
    export LIBSQLITE3_FLAGS=SQLITE_DISABLE_INTRINSIC
    binaries+=(--bin codex-command-runner --bin codex-windows-sandbox-setup)
    ;;
esac
cargo build "${args[@]}" "${binaries[@]}"
cd "$CODEX_REPO_ROOT"
python .keepalive-ci/scripts/package.py
