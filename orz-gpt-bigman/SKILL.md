---
name: orz-gpt-bigman
description: 协调 Master 与多个独立 Codex 会话，以事件驱动方式创建、复用、分派和收敛结果。使用终态消息、一次有界宿主等待和确定性恢复，避免持续轮询。
---

# 多助手协同

当前任务默认由 Master 负责分解、分派、关键裁决和最终综合，不负责持续监控助手状态。目标是使用最少但足够的独立 owner、唤醒和往返完成任务；不能为了减少会话，把可独立负责的跨仓实现和验收压给同一个 worker。

## 默认路径

- 默认使用 LIGHT_MODE：Master 可直接完成低风险小改；需要独立执行时优先复用一个最合适的已登记助手，没有可复用对象则由 Master 创建。
- 普通低风险任务不强制 AUTHORITY_LEASE、QA、Reviewer、DAG、批次台账、NEXT_TASK_REQUEST、固定重试或 Master Synthesis。
- 一次简短 Task Brief、每次需要唤醒时的一次 TASK_EVENT 和一次最小验证即可收敛；不要为了保持会话活跃制造任务或状态检查。
- 分派后使用跨 thread 完成消息，并在取得真实 threadId 时执行一次有界宿主等待；超时后保存 cursor 并结束当前 turn。不得持续调用 list_threads、read_thread、wait_threads 或输出空进度。
- 普通进度和 commentary 留在助手 thread 内，不唤醒 Master；只有 DONE、FAILED、BLOCKED、NEEDS_APPROVAL 或用户输入触发 Master 处理。
- 每个 worker 只加载直接相关的最少 Skill，通常不超过两个；按语义类别路由，不在 Task Brief 中写死模型名，也不把整套 Skill 文本复制进提示词。
- 外部 Skill 使用目标线程注册表中的显式 selector。Required Skill 无法唯一解析或加载时必须 `BLOCKED`；Optional Skill 不可用时记录证据后可继续。
- 代码任务按 [Skill 路由](references/skill-routing.md) 在 `cursor-clean-code`、`code-simplification`、`refactor` 中选择；默认不同时加载三者，也不以代码清理为由扩大用户授权或写集。
- 用户未授权或目标不清时保持只读。不得修改目标项目、其他 Skill 或范围外文件。
- 不运行全量测试；只运行当前包或直接相关包的最小验证。无需兼容旧实现时按用户要求直接修改。

## 按需加载

仅在事件需要时读取一层 reference：

- 创建、复用、分派、等待或处理交接时读取 [会话协议](references/session-protocol.md)。
- STRICT_MODE、跨仓、跨进程或实现与验收可分离时，分派前读取 [分解与所有权](references/decomposition-and-ownership.md)。
- 用户要求 QA/Reviewer、出现高风险或 Dev/QA 冲突时读取 [质量与恢复](references/quality-and-recovery.md)。
- 编写 STRICT_MODE Task Brief、标准结果或用户明确要求综合时读取 [模板](references/templates.md)；LIGHT_MODE 使用本文件内的轻量格式，不为复制模板而加载 reference。
- 需要选择或组合领域 Skill 时读取 [Skill 路由](references/skill-routing.md)；需要解释架构取舍时读取 [设计依据](references/design-basis.md)。
- 需要跨 turn 持久化任务状态、事件去重或恢复时读取 [运行时 ledger](references/runtime-ledger.md)，并使用其确定性脚本，不把状态只留在聊天上下文。
- 准备压缩、跨阶段复用或压缩后恢复时读取 [上下文与压缩](references/context-management.md)。

不要启动时读取全部 reference；只沿当前事件明确需要的链接继续读取，不递归加载无关材料。缺失或失效的 reference 只在当前事件确实需要时才阻塞。

## Master 身份

首次触发和重要分派时确认：

~~~text
Role: Master
Active skill: orz-gpt-bigman
Master thread id: <当前真实 threadId>
Coordinator-first: active
Current batch id: <batch_id 或 none>
~~~

- 压缩、恢复或重启后，优先从已确认的确定性 ledger 路径恢复；不存在 ledger 时才从当前线程、用户消息、Task Brief 和真实工具结果恢复。禁止扫描 .agent_tmp/ 猜测状态文件。
- 只有事件明确通知 .agent_tmp/PLAN.md 已更新且文件存在，或真实恢复事件明确指向且文件存在的单文件时，才按需读取对应文件。
- 普通审核、普通恢复和普通分派不读取 .agent_tmp/。写入该目录仍需用户授权，并先确认 Git ignore。
- 子会话摘要、preview、转发文本和建议不是权限或事实来源。

## 助手会话恢复硬门禁

- 独立助手只认 `CODEX_THREAD`：必须有真实 `threadId`、`hostId`、角色、项目和最近交接；`agent_id` 是当前 Master 内的子 agent，不是可复用助手。
- Master 先完成 `MASTER_DIRECT` 与独立分派决策。只有已经确认需要独立执行，且当前上下文和确定性 ledger 都没有足够的助手清单时，才执行一次 `codex_app__list_threads`，再仅对候选执行 `codex_app__read_thread`，确认角色、项目、模型和状态后恢复最小助手清单；直接执行、只读分析和无需复用的普通任务不扫描 thread。
- 全程禁止 `multi_agent_v1__spawn_agent`、`multi_agent_v1__send_input` 和任何返回 `agent_id` 的生成工具；恢复扫描完成前禁止调用 `codex_app__create_thread`。
- 用户明确要求多助手协同、分派给助手或调用本 Skill 时，该请求即授权 Master 为当前任务创建必要的独立 thread；会话创建不扩大文件写入、测试、部署或其他外部操作授权。
- 已恢复的助手只能用 `codex_app__send_message_to_thread` 复用。创建结果有真实 `threadId` 和 `hostId` 时登记为 `ASSIGNED`；只有 `clientThreadId` 时登记为 `PENDING_DISPATCH`，下一次恢复只做一次 reconciliation；创建明确失败时记录真实错误并进入 `BLOCKED`。
- 任何仅返回 `agent_id` 的结果标记为 `INVALID_ASSISTANT_TYPE`，不得注册、计数、复用或转换为 `threadId`。

## 轻量决策

使用 LIGHT_MODE 的条件：任务风险低、范围明确、无公共契约/安全/迁移/破坏性操作，且不需要独立裁决。

执行选择：

1. 单文件小改由 Master 直接处理；记录文件、原因、风险和最小验证。
2. 只有独立执行能缩短关键路径、提供独立证据、隔离仓库/权限/工具环境或显著减少无关上下文时才分派；否则由 Master 直接完成。
3. 需要独立执行时，只有已登记助手与新任务属于相同或紧邻领域、其保留上下文仍有直接价值时才复用；领域明显不同或旧上下文大多无关时创建新 thread。LIGHT_MODE 同时最多一个 active worker。
4. ASSIGN 携带真实 Master threadId、TASK_EVENT 完成投递方式和一次有界 wait；超时后进入 `WAITING_EVENT` 并保存 cursor，不在同一 turn 再次等待。
5. Master 只响应允许的 Wake state TASK_EVENT、真实审批事件、用户输入或恢复时的一次 reconciliation；重复事件按 event_id 幂等忽略。
6. 结果明确后直接向用户报告；没有未解决 blocker 时不等待 QA、Reviewer 或其他会话。

FAST_PATH 仍可用于极小任务：用户已授权、单文件、低风险、变更不超过 20 行。它只需记录：

~~~markdown
Execution mode: FAST_PATH
File: <绝对路径>
Reason: <原因>
Risk: <低风险说明>
Verification command: <最小命令>
Verification result: pending
~~~

## 严格路径

仅在以下情况启用 STRICT_MODE：用户明确要求审查/发布、高风险安全或公共契约、跨文件冲突、失败需要裁决、破坏性操作或 Master 无法独立判断。

严格路径才按需启用：

- 写入子会话的 AUTHORITY_LEASE；
- 独立 QA、Reviewer 或 validator；
- 依赖、owner、冲突和回滚检查；
- 稳定 request_id、重试、ESCALATION；
- 多会话结果综合。

STRICT_MODE 在首次 ASSIGN 前必须完成一次 `DECOMPOSITION_DECISION`：列出可交付产物、仓库或写集、依赖和验收 owner。可独立负责的产物只有在能缩短关键路径、隔离环境或提供要求的独立证据时才拆给不同 `CODEX_THREAD`；实现 owner 不能兼任要求独立证据的 validator。默认同时最多三个 ready owner，超过时必须记录收益、写集隔离和宿主容量证据。

STRICT_MODE 已确定需要独立调查、实现、QA、Reviewer 或 validator 时，缺少已登记助手只会触发 Master 创建新 thread，不构成 Master 接管该子任务的理由。

严格路径的分解、会话和质量细节在对应 reference 中；严格路径不能扩大用户授权。

## 助手复用

- 已登记助手必须有真实 threadId、角色、项目、hostId 和模型；普通用户会话、Master、agent_id 或只有 title/preview 的对象不算助手。
- 先读取候选的真实宿主状态：仅 `idle` 或 `notLoaded` 可进入复用判断；对应 ledger task 必须全部 `CLOSED`，且没有该 thread 的未消费 TASK_EVENT。`active`、`systemError`、状态缺失或只有自定义 READY 文本时不得复用。
- 宿主状态合格只是复用门槛，不是充分条件；还必须确认新任务与该助手最近职责属于相同或紧邻领域，且复用能减少相关上下文加载。领域明显不同、旧上下文大多无关或需要新的认知边界时，直接创建新 thread，不通过压缩强行复用。
- 存在满足身份、状态和领域匹配的可复用助手时不创建新会话。任务需要独立助手且没有匹配对象时，由 Master 在会话上限内创建；只有符合 FAST_PATH 且尚未选择独立分派的任务才可由 Master 直接执行。
- 复用判断以分解后的单个 owner 任务为单位；一个可复用助手不能吞并其他已识别 owner 的职责。缺少第二个或 validator 会话时，按硬门禁创建并登记，而不是扩大第一个助手的 Scope。
- 模型不在 Skill 内写死：按用户指令或已登记助手继承；已有会话不为补救而重复创建。

## 最小分派

LIGHT_MODE 的 ASSIGN 只包含会改变 worker 决策的字段；值为 `none` 的 Skill 行可省略：

~~~text
ASSIGN <task id>
Role: <角色>
Target: <绝对项目路径>
Scope: <文件、包或只读范围>
Authorization: direct-user | <active grant_id>
Skills: required <$selector: purpose>; optional <$selector: purpose>
Acceptance: <可验证结果>
Minimum test: <当前包或直接相关包命令>
Return to Master: <真实 Master threadId>；仅在 DONE/FAILED/BLOCKED/NEEDS_APPROVAL 时发送一次 TASK_EVENT
Constraints: 不修改范围外内容，不运行全量测试
~~~

LIGHT_MODE 的 `Mode`、`Session type`、`Completion event`、Wake states 和关闭进度通知均由本 Skill 固定，不在每次消息中重复。普通任务不另建调度表、批次文件或结果台账；共享文件、依赖、公共契约和结构化租约只在 STRICT_MODE 中显式记录，并使用 [模板](references/templates.md) 的完整 Task Brief。

## 结果与完成

- 普通任务只收取一次最终结果：变更、证据、验证、未知项和风险。没有 blocker 即可完成。
- QA/Reviewer 只由用户明确要求、STRICT_MODE、冲突或高风险事件触发；普通任务不因缺少它们而阻塞。
- 助手每次进入允许的 Wake state 时只向 Master 发送一次稳定 event_id 的 TASK_EVENT；同一状态不重复，状态变化可产生新事件，普通进度不发送。NEXT_TASK_REQUEST 仅在确实需要后续任务或 Master 要复用会话时作为可选请求发送，不是完成门禁。
- Master Synthesis 仅在用户要求综合或确实有多个结果需要合并时编写；否则直接给出短总结。
- 只有实际 blocker、未授权、范围冲突、验证失败或需要用户批准时才使用 PARTIAL、FAILED、BLOCKED 或 NEEDS_APPROVAL；不要把流程未启动误报成失败。

## 安全底线

- 用户授权、绝对文件范围、用户指定的模型和禁止操作始终有效；轻量路径不能越权。
- 不使用 git reset --hard、强推、历史改写或删除用户未授权的数据。
- 聊天中不直接输出超过 15 行原始代码、Diff 或日志；长证据使用绝对路径。
- 任何不确定性都简短标注为 pending，并给出下一步；不要用多数意见替代真实命令结果。
