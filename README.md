# Codex Skills

本仓库保存本机 Codex 使用的 skills。每个 skill 都以目录内的 `SKILL.md` 作为正式契约，Codex 会根据任务语义自动选择合适的 skill，也可以由用户明确点名调用。

## 目录说明

- `.system/`：Codex 随程序提供的内置 skills，可能随 Codex 更新而变化。
- 其他一级目录：本机安装或维护的自定义 skills。
- `orz-gpt-bigman/`：独立仓库 [skynit/orz-gpt-bigman](https://github.com/skynit/orz-gpt-bigman) 的安装副本。
- 凭据不写入仓库；需要外部服务的 skill 必须通过环境变量或运行环境提供凭据。

## 内置 Skills

| Skill | 作用 | 适用场景 |
|---|---|---|
| [`imagegen`](.system/imagegen/) | 生成或编辑位图图像，包括照片、插画、纹理、精灵、透明背景素材和视觉稿。 | 需要新建图片、修改已有图片或基于参考图生成变体时使用；不用于适合 HTML/CSS、SVG 或代码原生实现的视觉。 |
| [`openai-docs`](.system/openai-docs/) | 查询并引用 OpenAI、ChatGPT、Codex、模型、API、SDK 和自动化功能的官方文档。 | 询问 OpenAI 产品能力、价格、配置、故障排查、模型选择或 API 用法时使用。 |
| [`plugin-creator`](.system/plugin-creator/) | 创建或更新 Codex plugin 目录、manifest、可选资源和个人 marketplace 条目。 | 新建个人插件、补充插件结构或在本地开发中更新插件安装时使用。 |
| [`review-agent`](.system/review-agent/) | 对指定代码改动执行只读、缺陷优先的审查，输出可操作的问题。 | 审查未提交改动、分支差异、单个提交或其他 agent 委派的代码时使用。 |
| [`skill-creator`](.system/skill-creator/) | 创建或更新结构清晰、范围明确的 Codex skill 及其支持资源。 | 需要编写 `SKILL.md`、脚本、参考资料或校验现有 skill 时使用。 |
| [`skill-installer`](.system/skill-installer/) | 从官方列表或 GitHub 仓库安装 Codex skills。 | 查询可安装 skill、安装官方 skill，或从公开/私有 GitHub 仓库安装 skill 时使用。 |

## 自定义 Skills

| Skill | 作用 | 适用场景 |
|---|---|---|
| [`accept-code`](accept-code/) | 在真实 CWNAS Linux 设备上编译、部署并验收当前代码改动。 | 用户要求“验收代码”“真机验收”“部署验收”或在 NAS 上验证相关 API 时使用。 |
| [`botcf-batch-imagegen`](botcf-batch-imagegen/) | 通过 BotCF API 执行可恢复的批量图片生成，下载结果、转换格式并生成校验清单。 | 一次生成网站素材库、五行素材、Hero/Gallery 变体或其他成批视觉资产时使用；需要 `BOTCF_API_KEY` 环境变量。 |
| [`capture-conversations-to-vault`](capture-conversations-to-vault/) | 将当前对话和相关旁支会话整理进本机 Obsidian 知识库。 | 需要归档、总结、合并或更新 `/home/skynit/workspace/note` 中的知识笔记时使用。 |
| [`code-simplification`](code-simplification/) | 在不改变行为的前提下减少代码复杂度，提高可读性和可维护性。 | 功能已经正确，但实现过重、重复或难以理解时使用。 |
| [`codex-build`](codex-build/) | 把已冻结的实现规格交给 Codex 编码，再由 Claude 审查差异并迭代修正。 | 已有明确 `PLAN.md` 或锁定方案，需要委派中大型实现、迁移、修复或测试编写时使用。 |
| [`codex-review`](codex-review/) | 让 Codex 以只读批评者身份反复审查实现计划，直至批准或达到轮次上限。 | 已经有方案，希望在编码前对认证、迁移、并发、支付等高风险计划做跨模型压力测试时使用。 |
| [`cursor-clean-code`](cursor-clean-code/) | 约束代码改动保持小而清晰，强调命名、范围控制和克制的抽象。 | 编写、审查或重构代码，且需要避免过度设计和无关扩张时使用。 |
| [`diagram-design`](diagram-design/) | 创建带品牌风格的架构图、流程图、时序图、ER 图、状态图、数据图表等 HTML/SVG/PNG。 | 需要从描述、Draw.io 或 Mermaid 生成高质量可交付图示时使用。 |
| [`grill-me-codex`](grill-me-codex/) | 先通过逐问访谈锁定需求，再让 Codex 对计划进行只读对抗审查。 | 高风险设计尚有模糊决策，需要先澄清需求再做跨模型计划评审时使用。 |
| [`grill-with-docs-codex`](grill-with-docs-codex/) | 在访谈中同步校准 `CONTEXT.md`、术语和 ADR，然后让 Codex 审查最终计划。 | 项目已有领域文档，希望需求、文档和高风险实现计划一起收敛时使用。 |
| [`migrate-to-codex`](migrate-to-codex/) | 将支持的指令、skills、agents 和 MCP 配置迁移到 Codex 项目级或全局配置。 | 从 Claude Code 等既有配置迁移到 Codex，并需要生成、校验目标文件时使用。 |
| [`orz-gpt-bigman`](orz-gpt-bigman/) | 以事件驱动方式协调 Master 与多个独立 Codex 会话，负责创建、复用、分派和结果收敛。 | 需要跨会话并行处理独立工作，且要控制唤醒、等待、回调和恢复流程时使用。 |
| [`portable-engineering-patterns`](portable-engineering-patterns/) | 为 agent 协作型仓库建立可迁移的上下文、变更记录、工具边界、审批和测试门禁。 | 初始化、审计或重构仓库的 `AGENTS.md`、ADR 策略和工程治理规则时使用。 |
| [`refactor`](refactor/) | 进行渐进、外部行为不变的代码重构，包括提取函数、重命名、拆分大函数和改善类型。 | 需要消除代码异味或提升可维护性，但不希望进行整体重写时使用。 |
| [`review-code-plan`](review-code-plan/) | 在写代码前审查实现、重构、迁移、修复或发布计划。 | 需要发现计划中的风险、隐含假设、缺失验证、范围扩张或架构冲突时使用。 |
| [`setup-matt-pocock-skills`](setup-matt-pocock-skills/) | 为工程 skills 初始化 issue tracker、分诊标签词汇和领域文档布局。 | 首次在仓库中启用相关工程工作流时显式调用一次。 |
| [`to-spec`](to-spec/) | 将当前对话和代码上下文直接整理成规格，并发布到项目 issue tracker。 | 讨论已经充分、不需要再访谈，希望形成 PRD/规格任务时显式调用。 |
| [`ui-ux-pro-max`](ui-ux-pro-max/) | 基于本地 UI/UX 数据库提供风格、配色、字体、布局、动效、图表和技术栈建议。 | 设计、实现或审查 Web/移动端页面、组件、响应式布局、可访问性和交互体验时使用。 |

## 使用方式

Skills 默认安装在：

```text
${CODEX_HOME:-$HOME/.codex}/skills/<skill-name>/SKILL.md
```

通常直接描述任务即可触发对应 skill。`setup-matt-pocock-skills` 和 `to-spec` 禁用了自动模型调用，需要用户明确点名。具体流程、权限边界和依赖始终以各目录中的 `SKILL.md` 为准。

## 维护说明

- 修改 skill 后先检查其 `SKILL.md` frontmatter、引用路径和配套脚本。
- 不提交 API Key、Token、密码、私钥或本机生成的缓存文件。
- 各 skill 的许可证以其目录内的 `LICENSE`、`LICENSE.txt` 或第三方声明为准。
