# Skill 路由

Skill 路由只解决“哪个 worker 需要哪种能力”，不负责创建会话或扩大授权。selector 以目标线程当前注册表为准；磁盘目录、frontmatter name、Master 的注册表或历史记录不能替代目标线程的可用性证据。

## 路由表

| 任务意图 | 首选 Skill | 可选第二 Skill | 约束 |
|---|---|---|---|
| Codex/OpenAI 产品、API 或模型文档 | `openai-docs` | none | 只读取官方来源；不要把文档问题交给代码 worker |
| 代码计划、迁移或高风险方案审查 | `review-code-plan` | `codex-review` | 先完成计划证据，再决定是否实现 |
| UI、视觉、截图或响应式实现 | `ui-ux-pro-max` | 注册表存在时使用 `product-design:index` 或具体 Product Design selector | 只在 UI 任务加载；遵守 preview-first |
| 浏览器或页面运行时验证 | `browser:control-in-app-browser` | 注册表存在时使用 `product-design:audit` | 结果必须引用实际页面状态或截图 |
| Word、PDF、演示文稿或表格 | `documents:documents`、`pdf:pdf`、`presentations:Presentations`、`spreadsheets:Spreadsheets` | none | 每个 worker 只选与产物匹配的一个 |
| CWNAS 真机编译、部署和验收 | `accept-code` | `review-code-plan` | 仅用户明确要求真实设备验收时使用 |
| 生成或编辑位图素材 | `imagegen` | `botcf-batch-imagegen` | 未授权外部资源或批量生成时保持只读 |
| 已有行为正确，只需局部简化或提高可读性 | `code-simplification` | `cursor-clean-code` | 保持输入、输出、副作用、错误和边界行为；不得混入功能变化 |
| 明确的结构重构、代码坏味道或模块职责调整 | `refactor` | `cursor-clean-code` | 先确认测试或行为证据；设计模式只在解决已证实问题时使用 |
| 功能实现或缺陷修复存在范围漂移、过度设计风险 | `cursor-clean-code` | 项目专用 Skill | 只做最小完整改动；不要顺手清理范围外代码 |
| 通用代码搜索、实现或最小测试 | none | 项目专用 Skill | 优先使用项目指令和现有工具，避免无关 Skill |

## 代码质量 Skill

- `cursor-clean-code` 是范围与复杂度护栏，适用于功能实现、缺陷修复和重构；它不代表已获得重构范围，也不替代领域、框架或验收 Skill。
- `code-simplification` 用于行为已经明确且正确之后的局部可读性整理，例如深层嵌套、模糊命名、重复逻辑或无价值包装。它与功能实现默认分阶段处理。
- `refactor` 用于用户明确要求的结构性改进，例如拆分过长函数或大型模块、调整职责、改善类型和处理已确认的代码坏味道。不得仅因为 Skill 展示了 Builder、Strategy 等模式就引入它们。
- 默认只选择一个主代码质量 Skill：局部简化选择 `code-simplification`，结构重构选择 `refactor`。需要控制范围时再搭配 `cursor-clean-code`，不要因三者相关就全部加载。
- 任务还需要项目或领域 Skill 时，优先保留决定正确性的领域 Skill。若超过两个 Skill，把纯清理拆成后续 worker，或把最小范围约束直接写入当前 Task Brief 的 Scope、Acceptance 和禁止项。
- 只读审查可以使用 `refactor` 或 `code-simplification` 识别问题，但 Task Brief 必须写明 `read-only`；Skill 选择本身不授权修改代码、测试、提交或部署。

## 注入规则

1. Task Brief 使用 `$selector` 显式调用，分别列出 Required 和 Optional；每个 Skill 只说明与当前验收直接相关的一个用途，不复制完整 `SKILL.md`。
2. selector 必须从目标线程注册表原样取得，不能从文件夹名、插件名或 frontmatter name 推导；同名或多来源无法唯一解析时视为冲突。
3. worker 开始主要工作前读取所选 Skill 的完整 `SKILL.md` 并确认其必需工具可用。Required 失败时 `BLOCKED`；Optional 失败时记录 `unavailable` 后可继续。
4. 一个 worker 默认最多加载两个直接相关 Skill；第三个能力拆到后续 worker，除非用户明确要求组合。
5. 领域 Skill 只影响该 worker 的工作方法，不改变 Master 的权限、文件范围、测试范围或事件协议。
6. 不因为“可能有帮助”加载 Skill；没有明确输入、输出和验收关系时写 `none`。
7. worker 返回 requested、loaded、unavailable、冲突和目标注册表提供的 source locator。STRICT_MODE 对每个 loaded Skill 额外返回注册表中的 package/version；无版本时返回完整 `SKILL.md` 的 SHA-256，格式为 `sha256:<64 lowercase hex>`。本地 source locator 的摘要由 Master 使用 ledger 脚本复算匹配后记录；Master 再接受 DONE。
