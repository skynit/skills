# orz-gpt-bigman

面向 Codex 多任务协作的事件驱动协调 Skill。它让当前任务作为 Master，在权限和写集边界内创建或复用独立 Codex task/thread，分派工作，并通过终态事件收敛结果。

## 主要能力

- 默认使用轻量协调，只在独立执行能缩短关键路径、隔离环境或提供独立证据时分派工作。
- 为高风险、跨仓、公共契约、冲突裁决或明确审核请求提供严格模式。
- 通过真实 `threadId` 和 `hostId` 识别独立会话，不把当前任务内的 `agent_id` 当作可复用助手。
- 使用终态消息和一次有界宿主等待，避免持续轮询或空进度唤醒。
- 支持 Required/Optional 外部 Skill selector 的解析、加载证据和失败处理。
- 在跨 turn、上下文压缩和恢复时使用确定性 checkpoint 与 runtime ledger。
- 保留用户授权、绝对路径、最小测试和 owner 边界，不因协调流程扩大操作权限。

## 适用场景

适用于需要由一个 Master 协调多个独立 Codex task/thread 的工作，例如跨仓实现与验收、实现与独立 QA 分离、并行调查以及高风险变更审核。

普通问答、单文件低风险修改或无法从独立执行获益的任务，通常应由当前任务直接完成。

## 安装

将仓库克隆到 Codex skills 目录：

```bash
git clone git@github.com:skynit/orz-gpt-bigman.git ~/.codex/skills/orz-gpt-bigman
```

目录名应保持为 `orz-gpt-bigman`。安装后，在新的 Codex 任务中显式调用：

```text
使用 $orz-gpt-bigman 协调多个独立任务完成这项工作。
```

该 Skill 需要运行环境提供 Codex task/thread 的创建、读取、消息投递和有界等待能力。具体可用工具以当前 Codex 环境为准。

## 工作模式

### LIGHT_MODE

默认模式。Master 先判断是否需要独立分派；需要时最多保持一个 active worker，发送简短 ASSIGN，并只处理 `DONE`、`FAILED`、`BLOCKED`、`NEEDS_APPROVAL` 或用户输入等有效唤醒。

### STRICT_MODE

用于用户明确要求审查或发布、高风险安全或公共契约、跨文件冲突、破坏性操作及需要独立裁决的工作。启用分解决策、owner/validator 分离、结构化交接和更严格的恢复规则。

## 外部 Skill

分派可声明 Required 或 Optional Skill selector。selector 必须在目标线程的可用 Skill 注册表中唯一解析：

- Required Skill 无法解析或加载时，任务进入 `BLOCKED`。
- Optional Skill 不可用时，记录 source locator 和失败证据后可继续。
- 只加载会实际改变 worker 决策的最少 Skill，通常不超过两个。

详细规则见 [Skill 路由](references/skill-routing.md) 和 [会话协议](references/session-protocol.md)。

## 上下文压缩

只有上下文接近窗口限制、跨阶段交接或后续仍需复用当前 task/thread 时才进行压缩。压缩前写入确定性 checkpoint；恢复时优先读取 ledger，而不是依赖聊天摘要猜测状态。

详细规则见 [上下文与压缩](references/context-management.md) 和 [运行时 ledger](references/runtime-ledger.md)。

## 仓库结构

```text
orz-gpt-bigman/
|-- SKILL.md                         Skill 入口与核心决策规则
|-- agents/openai.yaml               Codex UI 元数据
|-- references/                      按事件加载的协议与设计说明
|-- scripts/orz_state.py             确定性 runtime ledger 工具
`-- tests/                            ledger 与 Skill 契约测试
```

核心入口是 [SKILL.md](SKILL.md)。不要在任务启动时一次性加载全部 references，只读取当前事件明确需要的文件。

## 验证

在仓库根目录运行当前 Skill 的最小测试：

```bash
python -m unittest discover -s tests -v
python ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```

不需要运行其他 Skill 或工作区的全量测试。

## 安全边界

- 创建或复用 task/thread 不等于获得源码修改、测试、部署或外部操作权限。
- 未授权或目标不清时保持只读。
- 不使用强推、历史改写或破坏性 Git 操作。
- 不通过压缩强行复用跨领域会话，也不以代码清理为由扩大写集。
