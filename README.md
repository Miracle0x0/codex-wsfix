# Codex WebSocket 构建与发布

将 [tolgaergin 在 issue #28295 中提供的修复](https://github.com/openai/codex/issues/28295#issuecomment-4713213667) 移植到 Codex **0.157.0**，并开放内置 OpenAI provider 的 WebSocket 开关与建连超时配置，用 GitHub Actions 测试、编译并发布非官方 GitHub Release。

已发布 **0.155.1-keepalive.1**：**[下载 Linux x64 / Apple Silicon 安装包](https://github.com/arusuki/codex-wsfix/releases/tag/codex-v0.155.1-keepalive.1-build.35551943899.1)**，包含 keepalive 修复。当前源码为 **0.157.0-keepalive.5**，经上游源码核对后保留两份补丁及下述配置功能，尚未发布。完整解压安装包后运行 `bin/codex`，保留同级资源目录。[首次 Actions 运行记录](https://github.com/arusuki/codex-wsfix/actions/runs/35551943899)与[验证记录](VALIDATION.md)可供核对。

## 修复内容

Responses WebSocket 的 pump 每 30 秒主动发送一个空 Ping，延迟首次触发并跳过错过的 tick；发送失败通过现有错误通道报告。它针对安静连接被中间代理断开的情况，不保证解决所有重连原因，也不把评论中的具体 CDN 超时推断当作已验证事实。

- 原作者提交：[320a3c032f5abfefdbc8b6c78321aaae08250bd8](https://github.com/tolgaergin/codex/commit/320a3c032f5abfefdbc8b6c78321aaae08250bd8)。原始 diff 保留在 `patches/original-320a3c0.patch`。
- 保活补丁：`patches/keepalive.patch`。保留原方案的定时器和错误处理，适配新版 `WebSocketConnection`；测试使用现有 loopback connector，确认静默期间连续发出两个 Ping。
- 配置补丁：[`patches/openai-transport.patch`](patches/openai-transport.patch)。增加两个可选顶层配置键，在现有配置加载链路中覆盖内置 OpenAI 的对应字段。省略时继承上游默认值，保留认证、请求头和其他能力。
- 上游固定在 `rust-v0.157.0` / `00c972ed5d6ff6499317fd41b7f23605b8e6850d`。该版本尚无主动定时 Ping，也未开放内置 OpenAI 的对应配置入口；两份补丁仅按新基线更新行号与文件索引，功能和上下文不变。`source.json` 的 `patches` 按应用顺序记录每份补丁的路径与 SHA-256，`patched_files` 记录修改范围。
- 不改变 `model_provider`，不需要迁移已有对话。

## OpenAI 传输配置

在用户级 `~/.codex/config.toml` 的顶层设置，放在任何 `[section]` 之前：

```toml
openai_supports_websockets = false
openai_websocket_connect_timeout_ms = 5000
```

| 配置项 | 作用 | 省略时 |
|---|---|---|
| `openai_supports_websockets` | 是否启用内置 OpenAI 的 Responses WebSocket；`false` 直接使用 HTTP，跳过 WebSocket 预连接与预热 | 继承上游，当前为 `true` |
| `openai_websocket_connect_timeout_ms` | 单次 WebSocket 建连超时，单位毫秒 | 继承上游，当前为 `15000` |

两项独立可选。仅调整超时时，只设置第二项即可；开关为 `false` 时，普通模型请求不会使用 WebSocket 建连超时。`0` 表示零时长超时，不表示无限等待。流响应空闲超时是另一项现有 provider 设置，本补丁没有新增其 OpenAI 顶层覆盖键。

默认 provider 已是 `openai`，无需另配名称或认证。选中自定义 provider 时，继续使用其原有配置。这两个键遵循现有 provider 配置的来源规则：接受用户级配置和 CLI `-c` 覆盖，仓库内 `.codex/config.toml` 按项目层过滤规则处理。配置作用于新加载的会话，不提供运行中会话热更新。[方案评估与维护位置](OPENAI_TRANSPORT.md)说明了补丁范围和版本核对方式。

## 首次部署

将本项目的**完整内容（包括 `.github`）**提交到你自己的 GitHub 仓库默认分支。可使用独立仓库，不必 fork 整个 Codex。以下示例以 `arusuki/codex-wsfix` 为目标；使用其他账号时替换仓库名。

```bash
cd codex-keepalive-ci
gh auth status
git init -b main
git add .
git commit -m "Add pinned Codex keepalive build and release CI"
gh repo create arusuki/codex-wsfix --public --source . --remote origin --push
```

若仓库已存在，正常提交推送到该仓库即可，不要再次运行 `gh repo create`。命令行推送 workflow 需要 GitHub 登录凭证具有相应 workflow 写权限。

首次推送到 `main` / `master` 会自动构建 Linux x64 + Apple Silicon 并发布；后续修改 workflow、补丁、source.json、scripts 或 tests 也会触发。只修改 README 不会触发。

也可以在网页 **Actions → Build patched Codex → Run workflow** 中启动，或运行：

```bash
gh workflow run build-release.yml --repo arusuki/codex-wsfix \
  -f targets=linux-and-apple-silicon -f publish=true
```

手动选择 `publish=false` 时只生成 Actions artifacts；选择 `true` 时仅在测试和全部所选平台都成功后发布 Release。发布只使用仓库自带的 `GITHUB_TOKEN`，不需要保存个人 PAT。仓库或组织策略必须允许该 workflow 的 `contents: write` 权限。

## 平台

| `targets` | 平台 | Runner |
|---|---|---|
| `linux-and-apple-silicon`（默认） | Linux x64 + Apple Silicon | 两个平台 |
| `linux-x64` | Linux x86_64 musl | ubuntu-24.04 |
| `linux-arm64` | Linux ARM64 musl | ubuntu-24.04-arm |
| `macos-arm64` | Apple Silicon | macos-15 |
| `macos-x64` | Intel macOS | macos-15-intel |
| `windows-x64` | Windows x64 MSVC | windows-2022 |
| `all` | 上述五个平台 | 各自原生 runner |

构建采用普通 GitHub hosted runners，无需 OpenAI 内部 runner、签名密钥或私有缓存。默认构建 Linux x64 + Apple Silicon。公开仓库标准 runner 的计费规则见 [GitHub 官方说明](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)。

## 流程和产物

1. 读取固定上游 commit 和目标平台。
2. 校验全部补丁 SHA-256、上游 SHA、工作区及 `git apply --check`，随后应用两份补丁；任一不符即停止。该官方 tag 的 Cargo.lock 中 155 个本地 workspace 包版本仍为 `0.0.0`；准备脚本仅将这些本地条目对齐到 `0.157.0`，并验证整个修正后的锁文件哈希。第三方依赖的版本、来源和校验值保持不变，后续构建和测试继续使用 `--locked`。
3. 测试与各平台发布构建分别缓存 Cargo 下载内容和第三方依赖编译产物，按 runner、目标平台、构建用途、Rust 编译器及编译环境区分；锁文件指纹排除本地包版本，依赖更新时可恢复相同环境的旧缓存。新缓存未精确命中时，按目标平台前缀读取已有的 `cargo-<target>-*` 下载缓存，Linux GNU 测试也可使用已有 musl 下载缓存。缓存不保存 Codex workspace 编译产物或工具安装目录，成功运行后保存新缓存。
4. 运行 Rust 格式检查、schema 生成一致性检查、keepalive 定向回归、`codex-api` 与 `codex-config` 测试，以及 `codex-core` 的 OpenAI 配置和传输定向回归；零匹配的回归测试同样失败。使用上游 Rust 1.95.0、`Cargo.lock`、musl/MSVC/V8 配置构建（为普通 runner 的内存限制关闭 LTO、使用 16 个 codegen units）；缓存命中仍执行全部测试、构建及校验，V8 等预编译依赖使用上游校验机制。
5. Linux 先编译并计算 bwrap 摘要，再将摘要嵌入 CLI；Windows 保留 sandbox 辅助程序。
6. 使用上游规范打包器保留 `bin`、`codex-resources`、`codex-path` 和 `codex-package.json`，执行 `--version` / `--help` 冒烟检查。
7. 验证所有所选平台产物和校验值，先创建 draft，全部附件上传完成后再公开。

Release 包含平台安装包、各包 `.sha256`、总 `SHA256SUMS` 和 `build-info-<target>.json`。包内附带两份补丁、上游 LICENSE/NOTICE 和 `BUILD-INFO.json`，记录各补丁及修改后各源码文件的 SHA-256。Release tag 带 run ID / attempt，重复运行不会覆盖旧版本。

**完整解压安装包**后运行 `bin/codex`（Windows 为 `bin/codex.exe`），或将这个 `bin` 目录加入 PATH。不要只复制单个可执行文件，否则会丢失必要的资源。`codex --version` 保留上游版本，补丁身份见包名和 `BUILD-INFO.json`。

这是 CLI / 内置 app-server 的非官方构建，不是 Codex 桌面应用安装包。没有发行商代码签名或 macOS 公证，不包含独立 native voice runtime。

## 更新上游或补丁

当前刻意固定在已检查的稳定版，不会自动跟随可变的 `main`。上游新版发布时，更新 `source.json` 的 tag/完整 commit SHA，重新检查补丁、Rust 工具链、构建依赖及打包逻辑，更新 `patches` 中的哈希、`patched_files` 与 `normalized_lock_sha256`，递增 `patch_revision`，通过检查后再运行 workflow。仅改 tag 不会改变源码版本。配置补丁按现有配置符号定位，只在三个生产代码位置增加配置与赋值，不复制 OpenAI 默认定义；测试及 schema 随补丁独立维护。

上游合入某项等价功能后，移除对应补丁及其测试配置；全部功能均已提供时切回官方发行版。工作流不会用 `git apply || true` 忽略冲突，也不会悄悄发布未修复的程序。

## 本地验证

```bash
python3 -m unittest discover -s tests -v
actionlint .github/workflows/build-release.yml
git clone --depth 1 --branch rust-v0.157.0 https://github.com/openai/codex.git upstream
python3 scripts/prepare.py upstream
cd upstream/codex-rs
just test --locked -p codex-api -E 'test(pump_task_sends_keepalive_pings)'
just test --locked -p codex-api
just write-config-schema
just test --locked -p codex-config
cargo build --locked --bin codex
just test --locked -p codex-core --lib -E 'test(openai_transport)'
just test --locked -p codex-core --test all -E 'test(openai_transport_connect_timeout_from_config_file) | test(responses_mode_stream_cli_disables_openai_websockets_from_config_file)'
```

完整构建和跨平台运行状态以实际 GitHub Actions 记录为准，见 `VALIDATION.md` 记录本次已完成的验证。
