# portable-engineering-patterns

一个可跨项目移植的 agent 工程治理 skill：把 agent 辅助开发拆成**上下文、记录、边界、验证、元治理**五个平面，让任何代码库都能逐步建立可执行、可验证、不拖慢 agent 的协作规则。

> English: A portable agent-engineering skill extracted from `deepseek-harness`. It turns AGENTS.md tiers, Agent Notes/ADRs, risk-based execution boundaries, and evidence-tier testing into an adoptable, language-agnostic workflow.

## 核心思想

| 平面 | 解决的问题 | 主要机制 |
|---|---|---|
| Context | agent 动手前需要知道什么 | 根/子树 `AGENTS.md`、分层文档、skills |
| Record | 代码为什么长这样、放弃了什么 | Agent Notes/ADR、conventional commits |
| Boundary | agent 能做什么、何时需要审批 | 普通开发默认放行，只对高风险效果设防 |
| Verification | 怎么证明改对了 | 聚焦测试、快照、真实入口 e2e、CI 矩阵 |
| Meta-governance | 谁在机械执行这些规则 | 验证脚本、git hooks、gate runner、CI |

关键原则：

- 每个事实只有一个归宿，其他地方只放链接。
- 优先机器可检查的规则，而不是口头约定。
- **普通开发默认放行**：读代码、编辑 workspace、跑测试/构建/lint、本地 git 不需要审批。
- **只对不可逆或外部效果要求审批**：发布、部署、凭证、系统/服务状态、破坏性数据、workspace 外操作。
- 只在受保护的高风险边界上 fail-closed，不让审批组件拖垮正常开发循环。

## 仓库结构

```text
.
├── README.md
├── SKILL.md                  # skill 主体
├── agents/
│   └── openai.yaml           # Codex/OpenAI 侧调用元数据
└── references/
    ├── methodology.md        # 分阶段落地方法论
    └── templates/
        ├── AGENTS.md         # 跨项目根 AGENTS.md 模板
        ├── SUBTREE-AGENTS.md # 子树 AGENTS.md 模板
        ├── AGENT-NOTE.md     # Agent Note/ADR 模板
        └── TESTING-POLICY.md # 测试策略模板
```

## 安装

### Claude Code

把整个仓库目录复制或软链到项目的 `.agents/skills/` 下：

```sh
mkdir -p /path/to/project/.agents/skills
cp -R portable-engineering-patterns /path/to/project/.agents/skills/
```

也可以软链：

```sh
ln -s "$(pwd)" /path/to/project/.agents/skills/portable-engineering-patterns
```

### Codex / OpenAI

复制整个目录到 skill 扫描根目录；`agents/openai.yaml` 已包含展示名、简介和默认 prompt。

### 其他 agent

只要该 agent 支持 `SKILL.md` 或 Markdown skill 目录，就把本仓库目录放到它的 skill 根目录下。skill 内部全部使用相对路径，移动后无需修改。

## 使用

按 skill 名调用：

```text
使用 portable-engineering-patterns 初始化这个仓库的 agent 协作规则
```

然后按 `SKILL.md` 的八步流程执行：

1. 盘点仓库真实命令和高风险动作。
2. 建立上下文平面：根 `AGENTS.md`、子树 `AGENTS.md`、分层文档。
3. 建立记录平面：`.agents/notes/` 路径化 Agent Notes 和格式验证。
4. 建立边界平面：普通开发默认允许，高风险效果单独审批。
5. 建立验证平面：按证据分层，禁止仪式化全量测试。
6. 建立元治理：验证脚本、窄 hooks、穷举 CI。
7. 用一个 sentinel change 跑通闭环。
8. 按需增量教学，不一次堆满规则。

## 模板速查

| 模板 | 用途 |
|---|---|
| `references/templates/AGENTS.md` | 新建仓库的根常驻规则 |
| `references/templates/SUBTREE-AGENTS.md` | 大目录的局部规则 |
| `references/templates/AGENT-NOTE.md` | proposed/implemented 决策记录骨架 |
| `references/templates/TESTING-POLICY.md` | 测试分层和证据选择规则 |

模板中的 `<PROJECT>`、`<SECRET>`、`<test>` 等占位符必须替换为真实命令；不要保留未验证的命令。

## 适配边界

这个 skill 是**指导框架，不是一刀切清单**：

- 普通 workspace 动作默认允许，不要给 agent 上逐动作审批。
- sandbox、per-call policy、scope isolation 只在不可信输入、多租户或真实事故后引入。
- 规则要以真实命令为准；没有执行过的命令不要写进 `AGENTS.md`。
- 不同语言和构建工具都适用；按项目替换命令和文档层级即可。

## 来源与许可证

方法论提取自 [`deepseek-harness`](https://github.com/skynit/deepseek-harness) 的 `AGENTS.md`、Agent Notes、测试策略和 skills 体系。

MIT License.
