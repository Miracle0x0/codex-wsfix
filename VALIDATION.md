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

## 尚未完成

尚未提交到用户的 GitHub 目标仓库，也未触发远程 workflow。因此 Linux / Apple Silicon 等平台的完整 CLI release 编译、安装包冒烟检查和 GitHub Release 发布尚未执行，不能把这个项目包当作已编译的 Codex 安装包。

默认发布矩阵已配置为 **Linux x64 + Apple Silicon**。仓库就绪后，推送到 `main` / `master` 会启动构建，只有 Rust 测试、全部平台编译、包检查及附件校验全部通过才会公开 Release。
