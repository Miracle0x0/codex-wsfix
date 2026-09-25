# 内置 OpenAI WebSocket 配置补丁评估

结论：`rust-v0.157.0` 仍未提供内置 OpenAI 的 WebSocket 开关与建连超时配置入口，因此保留两个顶层可选配置键方案。交付补丁为 `patches/openai-transport.patch`，与 keepalive 独立应用、校验和打包，构建修订号为 `keepalive.5`。

## 范围与取舍

新增 `openai_supports_websockets: Option<bool>` 与 `openai_websocket_connect_timeout_ms: Option<u64>`，在内置 provider 集合创建后、配置 provider 合并前应用显式值。最终选择仍经过上游原有逻辑，因此选中的 OpenAI 对象与 provider 集合中的对象一致。未指定时保留整个上游默认定义；选中其他 provider 时，其配置不受影响。

`supports_websockets` 和 `websocket_connect_timeout_ms` 已有完整传输实现，本补丁只开放内置 OpenAI 的配置入口，不修改 HTTP/WebSocket 客户端、重试、认证、远程协议或 provider 类型。单次建连超时仍由现有 `tokio::time::timeout` 执行。普通 Responses 请求关闭 WebSocket 后直接走 HTTP，预连接与预热也跳过；Realtime 等其他 WebSocket 功能不在此开关范围内。

生产代码集中在三个现有位置：配置类型增加两个可选字段、provider 构造点应用显式值、现有项目层 provider 配置过滤表增加两个键。其余变更为生成的 schema 和行为测试。不增加默认值副本、配置上下限、错误吞没或传输回退逻辑。

直接开放 `[model_providers.openai]` 会扩大修改范围：保留 ID 校验当前拒绝该项；合并函数对已存在的非 Bedrock provider 使用 `or_insert`，仅删除校验仍不会覆盖；整条替换又会丢失认证、请求头和其他默认能力。现有 provider 布尔字段无法区分省略与显式 `false`，因此通用局部覆盖需要另设计稀疏配置与合并语义。两个 `openai_*` 顶层键沿用 `openai_base_url` 的配置方式，更适合本项目持续维护小补丁的目标。

## 基线与定位

行号以下列未打补丁的稳定版源码为准：`00c972ed5d6ff6499317fd41b7f23605b8e6850d`。升级时以符号重新定位，不依赖行号机械替换。

| 文件（相对上游根目录） | 行号与定位符号 | 需要核对的语义 |
|---|---|---|
| `codex-rs/config/src/config_toml.rs` | 425，`ConfigToml.openai_base_url` | 两个新字段仍能从普通配置层反序列化 |
| `codex-rs/config/src/loader/mod.rs` | 88，`PROJECT_LOCAL_CONFIG_DENYLIST` | 与既有 provider 配置保持相同的来源规则 |
| `codex-rs/core/src/config/mod.rs` | 3772，`openai_base_url` / `built_in_model_providers` | 显式覆盖发生在构造后、合并和选择前 |
| `codex-rs/model-provider-info/src/lib.rs` | 514，`create_openai_provider`；684，`merge_configured_model_providers` | 默认定义继续由上游维护，合并不会丢弃已应用的覆盖 |
| `codex-rs/model-provider-info/src/lib.rs` | 508，`websocket_connect_timeout` | 配置毫秒值优先，省略时使用上游默认值 |
| `codex-rs/core/src/client.rs` | 1020，`responses_websocket_enabled`；1226，`connect_websocket` 内超时读取 | 客户端仍读取相同 provider 字段 |

0.156.0 新增的受管理 provider 选择逻辑仍发生在 provider 集合构造与合并之后，补丁保留其优先级。当前补丁统一使用三行上下文，并记录该稳定版的文件索引和行号。

## 验证与升级

配置测试从临时 `config.toml` 真实加载，比较完整 provider，覆盖省略、显式开关、仅修改超时、开关与超时组合、零超时、地址覆盖、自定义 provider 隔离，以及 CLI 高优先级覆盖。项目层测试验证两个键沿用原有过滤规则。传输测试检查 CLI 走 HTTP 时没有 WebSocket 握手，并使用接受 TCP 但不完成握手的本地服务器验证建连超时。实际执行结果见 [VALIDATION.md](VALIDATION.md)。

CI 校验生成的 schema 与补丁内版本一致，运行 `codex-config` 全部测试及 `codex-core` 的上述定向回归。app-server 的通用配置读写与远程线程配置协议未增加专门端到端测试，也不承诺运行中会话热更新。

升级上游时先核对表中的配置和传输语义，再重放补丁、运行 schema 生成器和定向测试，更新 `source.json` 的源码版本、两份补丁哈希、修改文件列表及锁文件哈希。上游增加正式等价配置后，移除对应本地实现和测试并使用正式配置，不维护旧键兼容层。
