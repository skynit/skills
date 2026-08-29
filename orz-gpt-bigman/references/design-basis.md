# 设计依据

本文件只记录经过审阅后采用的架构原则，不复制第三方项目代码。外部页面可能变化；链接用于追溯来源，运行时行为仍以当前工具契约和本 Skill 的协议为准。

审阅日期：2026-08-28

## 采用的原则

1. **角色与执行解耦**：按任务类别选择 planner、explorer、worker、reviewer，而不是在提示词中绑定某个模型名。
2. **协调器与 worker 分离**：Master 负责分解、调度、验证和综合；worker 负责一个有界、单一 owner 的任务，不能继续递归分派。
3. **外部状态优先**：任务状态、事件、结果引用和重试记录进入显式 ledger；不能只依赖聊天上下文或助手自报。
4. **独立上下文与小结果回传**：worker 在独立 thread 中运行，只回传结构化结果和证据引用，避免把完整历史复制给 Master。
5. **恢复和验证是生命周期的一部分**：崩溃、超时、重复事件和冲突必须可恢复或明确进入阻塞；完成必须由实际证据验证。
6. **按需加载 Skill**：只把当前 worker 需要的领域能力加载进提示词，避免把所有工具说明注入每个会话。
7. **最少但足够的并行度**：会话复用只用于相同或紧邻领域中仍有直接价值的上下文，不用于吞并独立 owner，也不通过压缩强行承接明显不同领域。写集和契约可隔离时拆分实现；要求独立证据时由不同 thread 验证。

## 参考页面

- [oh-my-opencode README](https://github.com/toel1234/oh-my-opencode)：角色化 agent、后台并行、类别路由、Skill 注入和 session recovery 的公开概览。
- [oh-my-opencode orchestration guide](https://github.com/toel1234/oh-my-opencode/blob/main/docs/guide/orchestration.md)：planning、orchestrator、specialist worker 分层，以及通过类别而非模型名分派。
- [ferrus](https://github.com/ferrus-dev/ferrus)：Supervisor/Executor/Reviewer 状态机、SQLite 运行时状态、作用域 artifact、崩溃恢复和无隐藏上下文。
- [Anthropic managed agents multiagent](https://github.com/anthropics/skills/blob/main/skills/claude-api/shared/managed-agents-multiagent.md)：独立上下文、并行 worker、只回传报告和廉价模型承接阅读型工作。

## 明确不照搬

- 不引入 tmux、特定 CLI、外部 provider 或第三方插件作为本 Skill 的前置依赖。
- 不把第三方 agent 名称、模型、并发数或 fallback 链写成永久规则。
- 不用另一个 LLM 充当周期性监控器；等待和去重优先由宿主工具或确定性 ledger 处理。
- 不把第三方项目的营销描述当成当前环境的运行时证明。
