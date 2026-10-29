# Codex Skills

本目录保存本机 Codex 使用的 skills，包括 Codex 内置 skill 和本机安装或维护的自定义 skill。每个 skill 的具体流程以目录内的 `SKILL.md` 为准；支持自动调用的 skill 可由 Codex 根据任务语义选择，也可以由用户明确点名调用。

## 目录说明

- `.system/`：Codex 随程序提供的内置 skills，可能随 Codex 更新而变化。
- 其他一级目录：本机安装或维护的自定义 skills。
- `orz-gpt-bigman/`：独立仓库 [skynit/orz-gpt-bigman](https://github.com/skynit/orz-gpt-bigman) 的安装副本。
- `goland-guide/`：显示名称为“goland指南”的 Go 开发统一入口，将 `cc-skills-golang` 的 46 个专题保存为按需读取的引用资料。
- Emil 的 14 个 UI、动画和 Swift skills：来自 [emilkowalski/skills](https://github.com/emilkowalski/skills)，用法见下方专节。
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
| [`deploy-kb-frontend`](deploy-kb-frontend/) | 构建并通过 SSH 部署 CWNAS 知识库 Vue 前端，备份旧版本并校验线上资源。 | 部署知识库前端或更新 `ai.cwnas.com` 静态资源时使用；不用于 Flutter 穿透平台或 Go 后端。 |
| [`deploy-tunnel-platform`](deploy-tunnel-platform/) | 快速部署 CWNAS Go 后端和 Flutter Web 前端到远程穿透平台，并执行备份、切换和服务检查。 | 部署、更新或重新发布穿透平台时使用；不用于 NAS 安装器或 ISO 构建。 |
| [`diagram-design`](diagram-design/) | 创建带品牌风格的架构图、流程图、时序图、ER 图、状态图、数据图表等 HTML/SVG/PNG。 | 需要从描述、Draw.io 或 Mermaid 生成高质量可交付图示时使用。 |
| [`executing-plans`](executing-plans/) | 按已有书面实现计划分阶段执行任务，并在检查点复核结果。 | 已有明确实施计划，需要在独立会话中逐项实现和验证时使用。 |
| [`finishing-a-development-branch`](finishing-a-development-branch/) | 在实现和测试完成后，核对环境并选择合并、PR、保留或清理分支。 | 开发分支已经完成，需要决定如何集成和收尾时使用。 |
| [`goland指南`（goland-guide）](goland-guide/SKILL.md) | 统一使用 `cc-skills-golang` 的全部 46 个专题，按任务读取相关引用资料。 | Go 编码、审查、调试、架构、测试、性能分析、依赖管理和工程配置时使用。 |
| [`grill-me-codex`](grill-me-codex/) | 先通过逐问访谈锁定需求，再让 Codex 对计划进行只读对抗审查。 | 高风险设计尚有模糊决策，需要先澄清需求再做跨模型计划评审时使用。 |
| [`grill-with-docs-codex`](grill-with-docs-codex/) | 在访谈中同步校准 `CONTEXT.md`、术语和 ADR，然后让 Codex 审查最终计划。 | 项目已有领域文档，希望需求、文档和高风险实现计划一起收敛时使用。 |
| [`iso-recreate`](iso-recreate/) | 通过完整构建路径重新生成 CWNAS Ubuntu 安装 ISO，包括全新的目标 RootFS。 | 安装器、系统包、服务、内核、initrd、启动流程或构建脚本有变化时使用。 |
| [`iso-refresh`](iso-refresh/) | 在现有安装 ISO 的 squashfs 中仅替换 cwnas 二进制和完整前端 root。 | 变更只涉及这两类载荷，希望复用已验证 ISO 时使用；其他变更应使用 `iso-recreate`。 |
| [`migrate-to-codex`](migrate-to-codex/) | 将支持的指令、skills、agents 和 MCP 配置迁移到 Codex 项目级或全局配置。 | 从 Claude Code 等既有配置迁移到 Codex，并需要生成、校验目标文件时使用。 |
| [`orz-gpt-bigman`](orz-gpt-bigman/) | 以事件驱动方式协调 Master 与多个独立 Codex 会话，负责创建、复用、分派和结果收敛。 | 需要跨会话并行处理独立工作，且要控制唤醒、等待、回调和恢复流程时使用。 |
| [`portable-engineering-patterns`](portable-engineering-patterns/) | 为 agent 协作型仓库建立可迁移的上下文、变更记录、工具边界、审批和测试门禁。 | 初始化、审计或重构仓库的 `AGENTS.md`、ADR 策略和工程治理规则时使用。 |
| [`refactor`](refactor/) | 进行渐进、外部行为不变的代码重构，包括提取函数、重命名、拆分大函数和改善类型。 | 需要消除代码异味或提升可维护性，但不希望进行整体重写时使用。 |
| [`requesting-code-review`](requesting-code-review/) | 为已完成任务或重要功能准备精确上下文，并请求独立代码审查。 | 完成阶段性工作、实现重大功能或准备合并前，希望验证实现符合要求时使用。 |
| [`review-code-plan`](review-code-plan/) | 在写代码前审查实现、重构、迁移、修复或发布计划。 | 需要发现计划中的风险、隐含假设、缺失验证、范围扩张或架构冲突时使用。 |
| [`review-code-simplification`](review-code-simplification/) | 只读审查未提交代码中的重复实现、复用机会和可减少的声明。 | 希望精简当前改动，同时保持行为、生命周期、并发和隐式接口语义不变时使用。 |
| [`sast-analysis`](sast-analysis/) | 建立代码库技术栈、入口、数据流和信任边界的安全架构图。 | 开始静态安全评估或缺少 `sast/architecture.md` 时首先使用。 |
| [`sast-businesslogic`](sast-businesslogic/) | 检查价格篡改、流程绕过、限制规避、竞态和奖励滥用等业务逻辑漏洞。 | 已有安全架构文档，需要审查可被利用的业务规则缺口时使用。 |
| [`sast-fileupload`](sast-fileupload/) | 发现并验证不安全文件上传、扩展名绕过和相关上传校验问题。 | 已有安全架构文档，需要审查上传入口时使用。 |
| [`sast-graphql`](sast-graphql/) | 检查 GraphQL operation 文档的动态拼接和注入风险。 | 项目使用 GraphQL，且需要排查 operation 字符串注入时使用。 |
| [`sast-hardcodedsecrets`](sast-hardcodedsecrets/) | 检查前端、移动端、客户端 bundle 和 HTML 中公开可达的硬编码凭据。 | 需要查找泄露的 API Key、Token、私钥或密码时使用。 |
| [`sast-idor`](sast-idor/) | 检查用户可控对象标识是否缺少所有权或授权校验。 | 需要排查 IDOR 和水平越权问题时使用。 |
| [`sast-jwt`](sast-jwt/) | 映射 JWT 签发与验证链路，并检查算法、签名、密钥、Header 和 Claim 校验弱点。 | 需要排查 Token 伪造或 JWT 认证绕过时使用。 |
| [`sast-missingauth`](sast-missingauth/) | 映射端点与角色权限，检查缺失认证和功能级授权问题。 | 需要排查未认证访问、垂直越权或管理员功能暴露时使用。 |
| [`sast-pathtraversal`](sast-pathtraversal/) | 追踪用户输入到动态文件路径，检查目录穿越和文件泄露风险。 | 需要排查 path traversal 或任意文件读取时使用。 |
| [`sast-rce`](sast-rce/) | 检查命令执行、eval 类入口和不安全反序列化等远程代码执行风险。 | 需要排查 RCE、命令注入或不安全反序列化时使用。 |
| [`sast-report`](sast-report/) | 汇总 `sast/` 下各专项结果，按严重性和机密性影响生成最终报告。 | 各漏洞专项检查完成后生成 `sast/final-report.md` 时使用。 |
| [`sast-sqli`](sast-sqli/) | 检查 SQL 字符串拼接、不安全 ORM 方法和动态标识符导致的注入。 | 需要排查 SQL 注入或数据库查询注入时使用。 |
| [`sast-ssrf`](sast-ssrf/) | 追踪用户输入到外部请求目标，检查服务端请求伪造风险。 | 需要排查 SSRF 或不受控出站请求时使用。 |
| [`sast-ssti`](sast-ssti/) | 检查动态模板字符串和用户输入组合导致的服务端模板注入。 | 需要排查 SSTI 或模板执行风险时使用。 |
| [`sast-xss`](sast-xss/) | 追踪用户输入到 HTML、JavaScript 和 DOM sink，检查跨站脚本风险。 | 需要排查存储型、反射型或 DOM XSS 时使用。 |
| [`sast-xxe`](sast-xxe/) | 检查 XML 解析器的外部实体防护以及用户输入可达性。 | 需要排查 XXE、XML 注入或文件/网络读取风险时使用。 |
| [`security-audit`](security-audit/) | 面向 Web、API、服务、CLI、库和守护进程执行以真实可利用性为中心的安全审计。 | 用户要求安全评审、漏洞审计或代码级渗透测试时使用。 |
| [`setup-matt-pocock-skills`](setup-matt-pocock-skills/) | 为工程 skills 初始化 issue tracker、分诊标签词汇和领域文档布局。 | 首次在仓库中启用相关工程工作流时显式调用一次。 |
| [`sub2api-imagegen`](sub2api-imagegen/) | 通过自建 Sub2API 网关调用 GPT Image 生成或编辑图片，支持 generate/edit/batch 三种子命令。 | 内置 `image_gen` 工具不可用，或用户明确要求走 Sub2API/CLI 路径时使用；凭据已内置在脚本里（内网专用 key，离开内网无效）。 |
| [`systematic-debugging`](systematic-debugging/) | 在提出修复前系统地复现问题、收集证据并定位根因。 | 遇到 bug、测试失败或任何非预期行为时使用。 |
| [`to-spec`](to-spec/) | 将当前对话和代码上下文直接整理成规格，并发布到项目 issue tracker。 | 讨论已经充分、不需要再访谈，希望形成 PRD/规格任务时显式调用。 |
| [`ui-ux-pro-max`](ui-ux-pro-max/) | 基于本地 UI/UX 数据库提供风格、配色、字体、布局、动效、图表和技术栈建议。 | 设计、实现或审查 Web/移动端页面、组件、响应式布局、可访问性和交互体验时使用。 |
| [`using-git-worktrees`](using-git-worktrees/) | 检测现有隔离环境，并通过平台能力或 Git worktree 创建独立工作区。 | 开始需要隔离的功能开发或执行实现计划前使用。 |
| [`verification-before-completion`](verification-before-completion/) | 要求在声称完成、修复或通过前运行最新验证并读取完整结果。 | 提交、创建 PR、交付任务或作出任何成功结论前使用。 |

## goland指南

[`goland指南`](goland-guide/SKILL.md) 的技能标识为 `goland-guide`，在 Codex 对话中用 `$goland-guide 具体任务` 调用，也支持根据 Go 开发任务自动选择。

这个 skill 将 `samber/cc-skills-golang` **2.0.1** 的全部 **46 个专题**整合到一个入口。引用资料是由入口按任务读取的普通文档，不会分别注册为独立 skill 或工具。完整目录见[专题索引](goland-guide/references/catalog.md)；例如代码风格指导保存在[代码风格引用](goland-guide/references/topics/golang-code-style/guide.md)。

```text
$goland-guide 审查当前 Go 包的代码风格和错误处理，只给建议，不修改源码。
$goland-guide 排查当前包中任务取消后仍继续运行的问题，先说明原因，再提出修复方案。
```

入口先选择与任务直接相关的专题，需要时再补充读取，避免一次加载全部资料。引用中的修改、测试和工具建议必须服从用户授权及项目规范；当前包的任务不会因为上游示例而自动扩大为全仓测试。

本机原 `cc-skills-golang` 插件已禁用，单独安装的 `golang-code-style` skill 已删除；代码风格等指导统一通过本入口读取。引用资料是随本 skill 保存的固定版本副本，使用时不依赖插件缓存，也不会自动跟随上游升级。来源和校验记录见 [source.json](goland-guide/references/source.json)，上游 MIT 许可证见 [LICENSE](goland-guide/references/LICENSE)。安装或迁移时应保留完整的 `goland-guide/` 目录。

## Emil UI、动画与 Swift Skills

这 14 个 skill 安装在本目录的同名子目录中。在 Codex 对话输入框中输入 `$技能名`，并在同一条消息中写明任务、目标文件或组件、技术栈和限制。下面的示例是对话提示词，不是终端命令。

| Skill | 用途 | 中文调用示例 |
|---|---|---|
| [`emil-design-eng`](emil-design-eng/SKILL.md) | 设计或审查 UI 细节，包括组件、排版、交互反馈和动画取舍。 | `$emil-design-eng 审查 src/components/Toolbar.tsx 的视觉和交互细节，只给建议，不修改代码。` |
| [`animate`](animate/SKILL.md) | 实现 Web 动画，选择属性、缓动、时长，并处理打断、退出和减少动态效果偏好。 | `$animate 给 src/components/Menu.tsx 添加打开和关闭动画，保持键盘操作即时响应。` |
| [`animate-expo`](animate-expo/SKILL.md) | 实现 React Native / Expo 的手势、弹簧、页面切换和触觉反馈。 | `$animate-expo 为 Expo 应用的 BottomSheet 添加拖拽关闭和速度衔接，使用现有 Reanimated。` |
| [`review-animations`](review-animations/SKILL.md) | 审查指定动画代码或差异，指出时长、缓动、性能和可访问性问题。 | `$review-animations 审查当前未提交的动画改动，列出问题和修改建议，不修改源码。` |
| [`improve-animations`](improve-animations/SKILL.md) | 审计代码库中的现有动画，输出按优先级排序的问题和可执行计划；源码只读。 | `$improve-animations 审计 src/components 中的现有动画，按影响排序并为前三项生成实施计划。` |
| [`find-animation-opportunities`](find-animation-opportunities/SKILL.md) | 寻找值得添加动画的交互，给出具体参数和不宜添加动画的位置；源码只读。 | `$find-animation-opportunities 检查设置页哪些状态变化适合加动画，只输出建议。` |
| [`animation-vocabulary`](animation-vocabulary/SKILL.md) | 将模糊的动效描述转换为准确术语。 | `$animation-vocabulary 列表项逐个延迟出现的动效叫什么？给出英文术语和中文解释。` |
| [`apple-design`](apple-design/SKILL.md) | 将 Apple 的流畅交互原则用于 Web 手势、弹簧、惯性、层次和可打断过渡。 | `$apple-design 改进 Web 抽屉的拖拽交互，让手势保留惯性并允许中途反向拖动。` |
| [`write-swift`](write-swift/SKILL.md) | 编写、审查或迁移 Swift，处理值类型、并发、协议、内存和性能问题。 | `$write-swift 检查 Sources/Store.swift 的并发隔离问题，按项目 Swift 版本提出修复建议。` |
| [`pick-ui-library`](pick-ui-library/SKILL.md) | 根据任务和已有依赖，从作者维护的列表中推荐 UI 库；需要显式调用。 | `$pick-ui-library 项目需要支持键盘操作的命令菜单，先检查 package.json，再推荐一个库。` |
| [`prototype`](prototype/SKILL.md) | 构建多个方向不同的组件原型，通过可视化选择器比较和选定；需要显式调用。 | `$prototype 为文件上传组件实现三个布局不同的方案，用切换器比较，沿用现有设计系统。` |
| [`mobile-native`](mobile-native/SKILL.md) | 改进移动 Web 的触摸、滚动、视口、安全区域和输入体验。 | `$mobile-native 修复移动端页面的 100vh、输入框缩放和底部安全区域问题。` |
| [`break-ui`](break-ui/SKILL.md) | 用真实极端数据检验 UI，添加演示数据与极端数据切换，并报告问题和修复建议。 | `$break-ui 给成员列表添加正常与极端数据切换，覆盖长邮箱、空列表和大计数，报告布局问题。` |
| [`ask-sonner`](ask-sonner/SKILL.md) | 配置、使用和排查 Sonner，包括异步提示、主题、样式和重复通知。 | `$ask-sonner 检查保存成功通知为什么出现两次，定位 Toaster 挂载和 toast 调用。` |

`pick-ui-library`、`prototype` 和 `review-animations` 的 `SKILL.md` 禁用了自动模型调用，使用时应明确点名。其余 skill 可根据任务自动选择；显式点名能更清楚地指定所需工作流。

这组 skill 在只收到技能名、没有具体问题时，会先返回准备提示并等待任务。把具体要求与技能名一起发送即可开始工作。`improve-animations` 和 `find-animation-opportunities` 不修改源码；`prototype`、`break-ui` 和动画实现类 skill 的任务可能涉及代码修改，需要在提示词中明确范围。只想审查时，应写明“只给建议，不修改代码”。

常见任务可以分步进行：

1. 不知道该加哪些动画：先用 `find-animation-opportunities` 提建议，再用 `animate` 实现选中的 Web 动画。
2. 已有动画需要改进：用 `review-animations` 审查指定改动，或用 `improve-animations` 审计并生成计划，再明确要求实施。
3. 组件方案未定：用 `prototype` 比较不同设计，再用 `break-ui` 检验极端数据下的布局。
4. 面向手机：移动 Web 使用 `mobile-native`，React Native / Expo 动画使用 `animate-expo`。

## SAST 使用顺序

安全专项 skill 依赖统一的架构上下文，推荐按以下顺序执行：

1. 使用 [`sast-analysis`](sast-analysis/) 生成 `sast/architecture.md`。
2. 根据目标运行一个或多个 `sast-*` 漏洞专项检查。
3. 使用 [`sast-report`](sast-report/) 汇总现有 `*-results.md`，生成 `sast/final-report.md`。

`security-audit` 提供通用安全审计方法；`sast-*` 则提供按漏洞类型拆分的结构化流程。它们都是审计工作流说明，不是独立的二进制扫描器。

## 使用方式

Skills 默认安装在：

```text
${CODEX_HOME:-$HOME/.codex}/skills/<skill-name>/SKILL.md
```

在 Codex 对话中，可以用 `$skill-name 具体任务` 明确调用，也可以直接描述任务，让 Codex 选择支持自动调用的 skill。例如：

```text
$animate 给 src/components/Dialog.tsx 添加进入和退出动画，沿用现有依赖。
$review-animations 审查 src/components/Dialog.tsx 的动画，只给建议。
```

`setup-matt-pocock-skills`、`to-spec`、`pick-ui-library`、`prototype` 和 `review-animations` 禁用了自动模型调用，需要用户明确点名。具体流程、权限边界和依赖始终以各目录中的 `SKILL.md` 为准。

## 维护说明

- 修改 skill 后先检查其 `SKILL.md` frontmatter、引用路径和配套脚本。
- 不提交 API Key、Token、密码、私钥或本机生成的缓存文件。
  - 已知例外：`sub2api-imagegen` 依用户决定内置了 Sub2API 网关的内网专用 key（离开内网无效），该 key 按公开信息对待，轮换时直接改脚本。
- 各 skill 的许可证以其目录内的 `LICENSE`、`LICENSE.txt` 或第三方声明为准。
