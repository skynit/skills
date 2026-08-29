# 会话与交接协议

这是轻量默认协议。只有当前事件需要创建、复用、分派、等待或交接时读取。

## 会话类型与恢复

- 独立助手必须是 `CODEX_THREAD`，同时记录真实 `threadId`、`hostId`、角色、项目、模型和状态；`agent_id` 永远是无效助手类型。
- Master 先判断任务能否 `MASTER_DIRECT`。只有已经决定独立分派，且当前上下文和 ledger 都没有足够助手清单时，才做一次 `codex_app__list_threads`，再对候选 `codex_app__read_thread`；直接执行、只读分析和无需复用的任务不扫描，确认后本轮也不重复扫描。
- 全程禁止 `multi_agent_v1__spawn_agent`、`multi_agent_v1__send_input` 和任何返回 `agent_id` 的生成工具。用户明确要求多助手协同、分派给助手或调用本 Skill 时，Master 可为当前任务创建必要的独立 thread；这不扩大目标项目的写入或验证授权。
- 恢复扫描完成前不创建新会话；扫描确认没有匹配助手且任务需要独立执行时，Master 用 `codex_app__create_thread` 创建。返回真实 `threadId` 和 `hostId` 时直接登记；只返回 `clientThreadId` 时以 `PENDING_DISPATCH` 保留异步创建事实；明确失败时进入 `BLOCKED`。
- 已有助手只通过 `codex_app__send_message_to_thread` 投递；任何只返回 `agent_id` 的调用立即标记 `INVALID_ASSISTANT_TYPE` 并停止该分派。

## 快速复用

1. 先按 [分解与所有权](decomposition-and-ownership.md) 得到 owner 任务并确认需要独立执行；再从当前 Master 已登记列表，或必要时的一次恢复扫描得到的助手清单，为每个 owner 找匹配的真实 threadId。
2. 使用 list/read 返回的真实 runtime status（以 [OpenAI App Server 文档](https://learn.chatgpt.com/docs/app-server)为准）：只有 `idle` 或 `notLoaded` 才可能复用；`active`、`systemError` 或状态缺失均不可复用。
3. 再用 `orz_state.py thread-lifecycle-ready` 检查该 thread 在当前 ledger 中至少有一项登记、所有旧任务均为 `CLOSED`，且没有未消费 TASK_EVENT。命令只返回 `lifecycle_ready`，不代表最终可复用；Master 还必须匹配角色、项目、模型和最近职责领域。助手自报的 READY 文本不属于状态证据。
4. 只有状态不明、存在审批、写入冲突或任务未关闭时才读取详细线程；不要每次执行三重 list/read/wait。
5. 没有可复用助手，或候选助手的旧上下文与新任务领域明显不同时，由 Master 先解析真实项目和目标环境，再创建新会话；不要通过压缩强行复用不相关上下文。`clientThreadId` 只能用于 `reserve`，不得传给要求真实 threadId 的工具；恢复后通过一次 list/read reconciliation 取得真实身份并 `bind`。

## 严格分派顺序

1. 首次 ASSIGN 前记录 `DECOMPOSITION_DECISION`，确认产物、owner、写集、依赖和 validator。
2. 对依赖已满足且写集隔离的 owner，一次完成复用或创建并分别 ASSIGN；不得把多个 owner 合成一个宽 Scope 来减少会话。
3. 对契约未冻结的下游任务，等待上游 owner 的 DONE，再以该结果引用作为 `Depends on` 证据分派；不轮询上游。
4. 验收标准要求独立证据时，所有实现 owner DONE 后分派独立 validator；不要求时，必须在分解决策中记录 `Independent validator: not-required` 及原因。
5. 同一 checkout 存在重叠写集时串行分派，或明确使用隔离 worktree；禁止两个本地 worker 并发写同一文件集合。

## 轻量 ASSIGN

普通任务发送一条消息即可：

~~~text
ASSIGN <task id>
Role: <角色>
Target: <绝对项目路径>
Scope: <文件/包/只读范围>
Authorization: direct-user
Skills: required <$selector: purpose>; optional <$selector: purpose>（均为 none 时省略）
Acceptance: <结果>
Minimum test: <最小命令>
Return to Master: <真实 Master threadId>；仅在 DONE/FAILED/BLOCKED/NEEDS_APPROVAL 时发送一次 TASK_EVENT
Constraints: 不修改范围外内容，不运行全量测试
~~~

LIGHT_MODE 的 Mode、Session type、Completion event、Wake states 和关闭进度通知由协议固定，不重复注入。只有 STRICT_MODE 才使用 [模板](templates.md) 的完整 Task Brief，补充 ownership、depends_on、delivery 和租约字段。

worker 开始主要工作前，从自己的可用 Skill 注册表解析 selector 并读取完整 `SKILL.md`。Required selector 缺失、歧义、依赖工具不可用或读取失败时立即发送 `BLOCKED` TASK_EVENT；Optional selector 不可用时记录原因并继续。最终交接必须列出 requested、loaded、unavailable 和冲突。STRICT_MODE 对每个已加载 Skill 还必须返回目标注册表的 package/version，或完整 `SKILL.md` 的 `sha256:<64 lowercase hex>`；使用本地摘要时 Master 通过 ledger 脚本按 source locator 复算。Master 先记录 Skill 证据，再记录 DONE TASK_EVENT。

低风险跨会话写入可在消息中直接给出范围；不要求先发送独立租约。高风险或严格路径才使用结构化租约：

~~~markdown
Message type: AUTHORITY_LEASE
grant_id: <稳定 id>
source_master_thread_id: <真实 Master threadId>
target_thread_id: <真实 child threadId>
scope: <限定任务>
allowed_files: <绝对路径清单>
allowed_tests: <当前包或直接相关包命令>
expires_at: <时间或任务结束>
forbidden_operations: <禁止动作>
Authorization: WRITE AUTHORIZED WITH SCOPED PACKAGE TESTS
Lease status: active
~~~

租约只能缩小用户授权；缺失或冲突时仅阻止该严格写入，不影响无关轻量任务。

## 事件驱动恢复

跨 thread 消息是 best-effort 完成投递，不是宿主回调注册：

1. ASSIGN 携带真实 Master threadId、Completion delivery、TASK_EVENT 和允许的 Wake states。
2. 助手执行期间不向 Master 发送普通进度、心跳或 commentary；这些内容只保留在助手 thread 中。
3. 助手进入 DONE、FAILED、BLOCKED 或 NEEDS_APPROVAL 时，通过 `codex_app__send_message_to_thread` 向 Master 投递一次 TASK_EVENT；投递失败最多用同一 event_id 重试一次。
4. Master 取得真实 threadId 后执行一次宿主托管的 `codex_app__wait_threads`；它用于接收终态、需要注意的状态或一个有界进度快照，不是循环轮询。
5. Master 使用 event_id 幂等处理事件；重复事件不重复审核、分派或综合。需要跨 turn 持久化时使用 [运行时 ledger](runtime-ledger.md)。

有界等待规则：

- 一次传入全部 active thread，最多 8 个目标，并复用已有 afterCursor；
- 不在等待前后调用 list_threads 或 read_thread 轮询；返回已含最终交接时不再读取同一 thread；
- commentary、普通进度和 unchanged 状态不触发处理；
- 超时且没有终态或审批事件时，保存 afterCursor，任务进入 `WAITING_EVENT` 并结束当前 turn；禁止在同一 turn 内再次调用 wait_threads；
- 用户输入、TASK_EVENT、审批或宿主恢复当前任务后，只做一次 reconciliation；超过已记录 deadline 时进入 `STALLED`，不得伪造 FAILED；
- `STALLED` 由 Master 根据真实状态转回 `IN_PROGRESS`/`WAITING_EVENT`，或进入 `FAILED`/`BLOCKED`。没有新的唤醒时，本 Skill 不声称能保证无人值守恢复。

## 交接

普通最终消息包含：

~~~markdown
Status: DONE | PARTIAL | FAILED | BLOCKED | NEEDS_APPROVAL
Task: <task id>
Role: <角色>
Changes: <变更或 none>
Evidence: <绝对路径和命令结果>
Unknowns: <未知项或 none>
Risks: <风险或 none>
Next action: <动作或 none>
~~~

缺少某个可选字段不阻塞轻量任务；只有授权、范围或结果本身缺失才报告 BLOCKED。

## 唤醒事件与后续任务

每次已分派任务进入允许的 Wake state 时，助手只为该状态发送一次：

~~~markdown
Message type: TASK_EVENT
Event id: <threadId>:<task_id>:<event_state>:<event_sequence>
Task: <task_id>
Source threadId: <真实 threadId>
State: DONE | FAILED | BLOCKED | NEEDS_APPROVAL
Result reference: <最终消息、绝对路径或结果引用>
Decision required: yes | no
Blocker: <none 或精确阻塞>
~~~

- event_id 必须稳定；同一状态的重试不得生成新 id。任务从 NEEDS_APPROVAL 等状态继续到 DONE，或再次进入同一状态时，使用新事件序号和新 event_id。
- TASK_EVENT 不附带完整日志、Diff 或会话历史，较长证据通过结果引用按需读取。
- TASK_EVENT 不是 NEXT_TASK_REQUEST；短生命周期助手完成后不主动索取新任务。
- 工具明确失败时可用同一 event_id 重试一次；只有工具成功才认为事件已投递。

助手确实需要后续任务或 Master 明确要持续复用该会话时，才可在 TASK_EVENT 后附加一次 NEXT_TASK_REQUEST：

~~~markdown
Message type: NEXT_TASK_REQUEST
Request id: <threadId>:<completed_task_id>:NEXT_TASK_REQUEST
Session id: <threadId>
Master thread id: <真实 Master threadId>
Completed task: <task id>
Available capacity: <范围>
Delivery: pending
~~~

request_id 必须稳定。工具明确失败时可用同一 request 重试一次；不强制 1s/2s/4s、四次投递、ESCALATION 或 MASTER_CHANNEL_UNAVAILABLE。无需新任务时不发送。

## 失败处理

- 轻量任务失败一次先报告真实错误和最小修复建议，不自动扩展会话。
- 只有用户要求继续、失败涉及高风险或出现冲突时，才切换 STRICT_MODE 并读取质量 reference。
- TASK_EVENT 投递失败时保留稳定 event_id 和原始错误，最多重试一次；不得改为周期性状态消息或心跳。
- 不得因缺少格式化交接、批次编号或可选请求而伪造成功；也不得因这些可选项缺失阻塞已完成的低风险任务。
