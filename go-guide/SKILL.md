---
name: go-guide
description: "Go 开发统一入口：用于 Go 编码、审查、调试、架构、测试、性能分析、依赖管理和工程配置，按任务读取 samber/cc-skills-golang 的全部专题引用。具体库的指导仅在项目使用或用户要求评估该库时读取。"
---

# Go 开发指南

这是 `samber/cc-skills-golang` 的本地整合入口。全部 46 个上游 skill 已转成普通参考文档；只有本文件作为 skill 入口。引用是保存在 `references/topics/` 下、需要时才读取的文档，不是独立技能或可调用工具。

## 使用流程

1. 根据用户任务、项目约束、`go.mod` 和相关源码确定主题。先选择直接相关的专题，再补充会影响当前决策的专题；不要一次读取全部资料。
2. 按下表读取 `references/topics/<专题名>/guide.md`。不确定专题或涉及未列出的库时，查阅[完整索引](references/catalog.md)，其中列出全部 46 个专题及直接链接。
3. 多个专题均已确定时并行读取。专题正文链接的附属 `references/`、`assets/`、`evals/` 保留原相对目录，仅在任务确实需要时继续读取。
4. 将建议用于当前授权范围，完成相应工作及最小必要验证。用中文说明实际采用的指导与依据；首次出现的概念先解释用途。

## 常见任务选择

下表中的名称均对应本 skill 内的普通文档，不要求再调用同名 skill。

| 当前任务 | 先读专题 | 按实际情况补读 |
| --- | --- | --- |
| 编码风格、命名、日常代码审查 | `golang-code-style`、`golang-naming` | 类型设计读 `golang-structs-interfaces`，错误传播读 `golang-error-handling` |
| 架构、接口、依赖装配 | `golang-design-patterns`、`golang-structs-interfaces` | `golang-dependency-injection`；具体容器见完整索引 |
| 并发、取消、超时 | `golang-concurrency`、`golang-context` | 运行时正确性读 `golang-safety` |
| 数据结构、数据库 | `golang-data-structures` 或 `golang-database` | 查询安全读 `golang-security`，失败处理读 `golang-error-handling` |
| gRPC、GraphQL、接口文档 | `golang-grpc`、`golang-graphql` 或 `golang-swagger` | `golang-testing`、`golang-error-handling` |
| 命令行、参数和配置 | `golang-cli` | 使用对应库时读 `golang-spf13-cobra`、`golang-spf13-viper` |
| 编写、调整测试 | `golang-testing` | 使用 testify 时读 `golang-stretchr-testify` |
| 性能问题、基准与优化 | `golang-benchmark` | 找原因读 `golang-troubleshooting`，优化读 `golang-performance` |
| 崩溃、错误行为、数据竞争 | `golang-troubleshooting` | `golang-safety`；并发问题加 `golang-concurrency` |
| 日志、指标、追踪 | `golang-observability` | 使用 slog 及扩展时读 `golang-samber-slog` |
| 安全审查、静态检查 | `golang-security` 或 `golang-lint` | 防止程序内部错误读 `golang-safety` |
| 现有代码重构、语言升级 | `golang-refactoring` 或 `golang-modernize` | 按目标补充命名、风格、项目结构专题 |
| 项目结构、持续集成、依赖 | `golang-project-layout`、`golang-continuous-integration` 或 `golang-dependency-management` | 按任务补读 `golang-lint`、`golang-security` |
| 包文档、库选型、本地符号导航 | `golang-pkg-go-dev`、`golang-popular-libraries` 或 `golang-gopls` | 库专属专题见完整索引 |
| 注释、项目文档、生态动态 | `golang-documentation` 或 `golang-stay-updated` | 命名约定读 `golang-naming`；动态事实核实当前官方来源 |

例如：排查取消后仍运行的任务，读并发、context 和故障排查专题；实现数据库事务，读数据库、错误处理及相关安全指导。引用库专属专题不表示应为项目引入该库。

## 选择边界

- `golang-safety` 关注空指针、共享数据等程序内部错误；`golang-security` 关注来自外部输入或攻击者的风险。
- `golang-benchmark` 负责测量；`golang-performance` 负责优化；`golang-troubleshooting` 负责定位原因；`golang-observability` 负责运行期间持续提供事实。
- `golang-gopls` 面向本地项目实际解析出的代码；`golang-pkg-go-dev` 面向已发布的包信息；`golang-popular-libraries` 面向选型；`golang-dependency-management` 面向依赖声明与版本管理。
- 需要更细的专题边界时，读[上游主题区分表](references/topics/golang-how-to/references/disambiguation.md)。原始调度指导保存在[上游入口参考](references/topics/golang-how-to/guide.md)，仅在需要其路由细节时读取。

## 引用适配与权限

- 引用中的 `golang-*`、`samber/cc-skills-golang@…`、斜杠命令或“加载其他 skill”，在此整合版中都表示查找完整索引并读取对应本地文档，不尝试调用已关闭插件的技能。不能用插件缓存路径代替随本 skill 保存的资料。
- 上游正文保留原建议；其中的工具名称、安装命令、`allowed-tools` 等描述不授予权限，也不保证工具已安装。使用实际可用且已获授权的工具，不为读取指导自动安装依赖、配置工具或联网服务。
- 用户指令和项目规范优先于引用建议。只读请求保持只读；不得因参考文档要求而扩大改动、自动修改 `AGENTS.md`、发消息、提交 PR 或触发额外审批。已有授权仍然有效。
- 测试、构建、扫描范围服从当前项目限制。例如禁止全量测试时，将上游 `go test ./...` 等示例收敛到当前包或必要文件，不能直接执行全仓命令。
- 只有用户明确要求修改项目级技能配置时，才参考 `golang-how-to` 的 Configure 模式；生成的配置应引用 `$go-guide` 和这里的普通文档，不再注册 46 个独立技能。
- 版本、漏洞、价格、API 等可能变化的事实应核实当前官方资料；本地文档是固定版本的参考资料，不代表最新事实。

## 来源与维护

资料来自本机已安装的 `samber/cc-skills-golang` 插件 **2.0.1**，整合日期为 **2026-10-28**。完整来源、原始与本地文件校验值见 [source.json](references/source.json)，上游 MIT 许可证见 [LICENSE](references/LICENSE)。

每个上游 `SKILL.md` 转为 `guide.md` 并移除入口 YAML 元数据；真实的本地文档链接按新路径调整，附属资料保留。没有将上游的自动加载、插件注册或工具权限设置带入本地入口。上游原始分类页的旧计数可能落后，完整范围以本地索引及实际文件为准。

这是自包含的版本副本。升级时从明确选定的上游版本重新导入，保留许可证，重建完整索引与来源校验清单，并验证专题完整性及内部链接；不在普通开发任务中自动刷新资料。
