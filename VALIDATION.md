# 验证记录

验证日期：2026-09-25。

上游：`openai/codex` 的 `rust-v0.157.0`，完整 commit 为 `00c972ed5d6ff6499317fd41b7f23605b8e6850d`。

## 0.157.0-keepalive.5：补丁点位更新

两份补丁仍有必要：上游尚无主动定时 Ping，也未提供内置 OpenAI 的 WebSocket 开关和建连超时配置入口。0.157.0 新增 WebSocket 网络策略检查及策略拒绝错误传播；保活发送仍使用同一 `WebSocketConnection` 和错误通道，沿用这些检查。配置覆盖仍位于内置 provider 构造后、合并和选择前。

旧补丁的 keepalive 连接与测试点位分别偏移 3、11 行；配置类型、过滤表、schema、provider 构造和测试模块点位分别偏移 12、4、44、37、52 行。两份补丁已重新生成；排除文件索引和 hunk 行号后，补丁逐行完全一致，功能代码、测试代码和上下文均未改动。已同步 `source.json` 中的补丁 SHA-256，修改范围仍为 9 个文件。

全新 checkout 的 `prepare.py` 通过固定提交、补丁应用、哈希和修改范围校验，准备结果与重定位工作区逐字节一致。锁文件以 0.157.0 的上游依赖为准，仅对齐 155 个本地包的版本；其余条目不变，规范化后的 SHA-256 为 `0ca2e7967026f5cb617a295909d8e0765ce115dd690a065d2055322908416967`。Rust 工具链仍为 1.95.0，现有打包入口未变。

本次按要求仅作静态核对和补丁点位更新，未进行本地构建、schema 生成或测试，也未运行 GitHub Actions 或发布。

## 0.156.1-keepalive.4：上游静态复核

比较 `rust-v0.156.0` 与 `rust-v0.156.1`（`b412ff32c417f855c2b2d1581b77058eed87c84b`）的完整差异：上游更新模型目录、模型选择提示及相关测试和快照，并递增 workspace 版本；两份补丁涉及的源码、schema、配置加载与传输实现均未改变。两份补丁仍有必要，内容、行号、上下文和 SHA-256 全部保持不变。

`git apply --check --verbose` 无偏移通过，`prepare.py` 的固定提交、补丁哈希、锁文件哈希和修改范围校验通过。上游 `Cargo.lock` 与 0.156.0 相同，准备脚本仍仅对齐 155 个本地包的版本；对齐为 `0.156.1` 后的 SHA-256 为 `d722f05fc760bcd1f5749ec452452d81058458b788df3b765b80500d757eba4a`。

本次按要求仅作源码差异与补丁应用核对，未进行本地构建、schema 生成或测试，也未运行 GitHub Actions 或发布。

## 0.156.0-keepalive.3：上游复核与补丁重定位

核对 `rust-v0.156.0`（`fe74a774532af67b5a4a3dec03ce9469e17f89af`）的源码后，两份补丁均保留。`codex-api` 的 `WsStream` 只响应收到的 Ping，下层 `codex-websocket-client` 也没有主动定时保活；内置 OpenAI 仍默认启用 WebSocket、使用 15000 毫秒建连超时，配置类型没有对应覆盖入口，且 `model_providers.openai` 仍属于禁止用户定义的保留 ID。

旧补丁在 0.156.0 上均可应用，但 keepalive 点位偏移 1–17 行，配置与 schema 点位也已移动。当前补丁按新基线重新生成文件索引、行号和上下文；配置构造处恢复普通三行上下文，保留上游新增的受管理 provider 选择逻辑。逐行比较确认，两份补丁的所有增删源码行与上一修订完全一致，修改范围仍为 9 个文件。

- 全新 checkout 的 `prepare.py`：源码 SHA、两份补丁 SHA-256、锁文件哈希、应用及修改文件范围检查均通过，结果与实际测试工作区逐字节一致。
- `Cargo.lock`：仅将 155 个本地包版本从 `0.0.0` 对齐为 `0.156.0`，其余锁文件数据不变；`cargo fetch --locked` 接受修正后的锁文件。SHA-256 为 `dd2d092e8d0d72ed5fb2ac221b04d71580497c520c745169ecbc09c2095e28f6`。
- 上游 `just fmt`：通过。
- `just test --locked -p codex-api`：**192 passed，0 skipped**，包含连续两个 Ping 的 keepalive 回归。
- `just test --locked -p codex-config`：**341 passed，0 skipped**，包含项目层 OpenAI 配置过滤回归。
- `just write-config-schema`：成功，生成结果与补丁中的 schema 逐字节一致。
- `cargo build --locked --bin codex`：Linux x64 开发构建成功，`--version` 返回 `codex-cli 0.156.0`，`--help` 冒烟检查通过。
- `codex-core --lib` 的 OpenAI 配置回归：**3 passed**，其余 2567 项因定向筛选未运行；验证默认值、独立覆盖、完整 provider 一致性、自定义 provider 隔离和 CLI 优先级。
- `codex-core --test all` 的传输定向回归：**2 passed**，其余 2002 项因定向筛选未运行；关闭 WebSocket 后 CLI 经 HTTP 完成请求且没有升级握手，100 毫秒配置能使未完成的 WebSocket 握手返回 `TransportError::Timeout`。
- 构建控制脚本：**10 passed**；Python 编译检查、Bash 语法检查及 `git diff --check` 通过。
- Rust 工具链仍为 1.95.0，打包入口参数和布局不变；上游 musl 安装脚本新增的 OpenSSL 3.6.4 构建由现有 workflow 直接调用，无需修改本地脚本。

本次本地验证使用 Linux x64、Rust 1.95.0、cargo-nextest 0.9.145 和 just 1.55.1，开发与测试构建关闭调试信息。依赖预先下载，V8 产物通过上游清单及文件校验；Rust 检查保持 `--locked`，网络测试未禁用。未运行整个 Rust workspace 测试、GitHub Actions 或跨平台 release 构建，0.156.0 版本尚未发布。

## 0.155.1-keepalive.2：OpenAI 传输配置

以下本地记录对应 2026-09-21 验证的 `rust-v0.155.1` / `be2951ea34f0d295ed0becf97079f92fa5f6950e`。

新增配置补丁为 `patches/openai-transport.patch`；原 keepalive 补丁不变。配置补丁修改 8 个文件，新增 289 行、删除 3 行，生产代码集中在配置类型、provider 构造与现有项目层过滤表三处，其余为 schema 和测试。

- 全新稳定版 checkout 的 `prepare.py`：两份补丁共同应用成功，源码 SHA、两份补丁哈希、锁文件与修改文件范围检查均通过。实际测试工作区的 9 个修改文件及锁文件与准备脚本结果逐字节一致。
- 同一份配置补丁在本地 `main` / `a866315` 上的 `git apply --check` 通过；该版本未编译或运行测试。
- `just write-config-schema` 成功；生成结果只增加两个顶层配置项。
- `just fmt` 通过。
- `just test --locked -p codex-config`：**304 passed，0 skipped**，包含新增项目层配置过滤测试。
- `just test --locked -p codex-core --lib -E 'test(openai_transport)'`：**3 passed**，其余 2488 项因定向筛选未运行；覆盖真实配置文件加载、默认值保留、零超时、完整 provider 一致性、自定义 provider 隔离和 CLI 覆盖优先级。
- 两份补丁共同应用后的 `cargo build --locked --bin codex`：Linux x64 开发构建成功，`--version` / `--help` 冒烟检查通过。
- `codex-core --test all` 的两项传输定向回归：**2 passed**，其余 1769 项因筛选未运行。CLI 从配置文件关闭 WebSocket 后成功通过 HTTP 完成请求，服务器收到的升级握手为零；本地 TCP 服务器保持握手未完成时，100 毫秒配置触发现有 `TransportError::Timeout`，整项测试耗时约 141 毫秒。
- 两份补丁共同应用后的 `just test --locked -p codex-api`：**182 passed，0 skipped**，包含连续发送两个 Ping 的 keepalive 回归。
- 构建控制脚本：**10 passed**；覆盖双补丁应用、各补丁篡改、第二份补丁冲突时不修改源码或锁文件、已有 builder 文件保留，以及原有产物验证。
- `actionlint 1.7.12` 通过（未启用可选 shellcheck / pyflakes）；Python 编译检查、Bash 语法检查和 `git diff --check` 通过。

本次本地验证使用 Linux x64、Rust 1.95.0、cargo-nextest 0.9.145，开发和测试构建关闭调试信息。未运行整个 Rust workspace 测试。新增配置版本尚未运行 GitHub Actions、跨平台 release 构建或发布；下面的双平台发布记录对应 `keepalive.1`。

## 0.155.1-keepalive.1：已完成的验证

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
