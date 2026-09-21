# 验证记录

验证日期：2026-09-21。

上游：`openai/codex` 的 `rust-v0.155.1`，完整 commit 为 `be2951ea34f0d295ed0becf97079f92fa5f6950e`。

## 已完成

- 在全新本地 checkout 上执行完整 `prepare.py`：通过源码 SHA、补丁 SHA-256、锁文件哈希、干净工作区、补丁应用及变更文件范围检查。
- 锁文件处理与 Cargo 自身生成的结果逐字节一致：只有 152 个本地 workspace 包的版本从 `0.0.0` 改为 `0.155.1`，第三方依赖、来源及校验值均未改变。
- 上游 `just fmt`：通过。
- keepalive 定向回归：`just test --locked -p codex-api -E 'test(pump_task_sends_keepalive_pings)'`，**1 passed**。
- 修改 crate 的全部测试：`just test --locked -p codex-api`，**182 passed，0 skipped**。
- 构建控制脚本测试：**8 passed**，覆盖默认双平台矩阵、固定源码、补丁完整性、重复应用拒绝、完整产物、损坏产物、缺失平台以及额外产物拒绝。
- GitHub Actions 配置：`actionlint 1.7.12` 通过（未运行可选 shellcheck / pyflakes；另行执行了 Bash 语法检查和 Python 编译检查）。
- `git diff --check`：通过。

本地 Rust 验证使用 Rust 1.95.0、cargo-nextest 0.9.145、just 1.51.0。当前容器缺少 pkg-config，实际测试使用已有 OpenSSL 的 include/library 路径；GitHub workflow 会显式安装原生测试依赖。

## GitHub Actions 与实际发布

已部署到 `arusuki/codex-wsfix`。[首次完整运行](https://github.com/arusuki/codex-wsfix/actions/runs/35551943899) 的 resolve、test、Linux build、Apple Silicon build 和 release 五个任务全部成功。

- 构建控制脚本测试：8 passed；keepalive 定向回归：1 passed；`codex-api`：182 passed，0 skipped；Rust 格式检查通过。
- Linux x64：`x86_64-unknown-linux-musl`，release 编译、完整安装包 `--version` / `--help` 冒烟检查和附件上传成功。
- Apple Silicon：`aarch64-apple-darwin`，在 `macos-15` 原生 runner 上完成相同检查并成功上传。
- 发布任务验证了所有所选平台的完整附件和 SHA-256，已将 draft 公开为 [Codex 0.155.1-keepalive.1](https://github.com/arusuki/codex-wsfix/releases/tag/codex-v0.155.1-keepalive.1-build.35551943899.1)。Release 包含两个安装包、两个独立校验文件、两个构建信息文件和 `SHA256SUMS`。
- CI 源码提交：`06c8ad07541252501102a05a6f954da859a724c0`。Release 产物的 GitHub SHA-256 摘要如下。

| 平台 | SHA-256 |
|---|---|
| Apple Silicon | `360b26b82896e1495b64d481c8c112cb1bad74eb60a135b8e0bc66b8320b2048` |
| Linux x64 | `3433fd678c2dc0eeada8cfa6c907df994f1b665bdb1b34c1a6626c02cdbcb50c` |

其他可选平台尚未运行。测试确认补丁会发送保活 Ping，但未在用户实际网络中验证重连症状是否消失。
