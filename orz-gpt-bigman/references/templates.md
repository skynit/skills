# 协同模板

模板按需复制，不是普通任务的完成门禁。

## 分解决策

STRICT_MODE、跨仓/跨进程或实现与验收可分离时，在首次 ASSIGN 前记录：

~~~yaml
Message type: DECOMPOSITION_DECISION
Mode: STRICT_MODE
Outputs:
  - task_id: <稳定 id>
    owner_role: <唯一 owner 角色>
    repository_or_package: <绝对根目录或包>
    write_set: <绝对路径或 read-only>
    depends_on: <task ids or none>
    acceptance: <独立可验证结果>
Execution: parallel | serial | staged
Delegation benefit: <关键路径、独立证据、环境隔离或上下文隔离>
Independent validator: <task id> | not-required
Single-worker exception: none | <允许的事实原因和风险>
~~~

`Single-worker exception` 不是自由说明项：只有不可拆分原子边界、无法隔离的重叠写集、当前任务本身负责冻结契约，或宿主真实无法取得会话时才可填写非 `none`。

## 严格 Task Brief

LIGHT_MODE 使用 `SKILL.md` 和会话协议中的轻量 ASSIGN，不加载或复制本模板。以下完整格式仅用于 STRICT_MODE：

~~~text
Task: <task id>
Role: <角色>
Scope: <绝对路径、包或只读范围>
Mode: STRICT_MODE
Ownership: <唯一产物和写集>
Depends on: <task ids or none>
Authorization: direct-user | <grant_id>
Session type: CODEX_THREAD
Assistant threadId: <真实 threadId>
Master threadId: <真实 Master threadId>
Required skills: <$selector (one-line purpose); ... | none>
Optional skills: <$selector (one-line purpose); ... | none>
Completion delivery: cross-thread-message | host-wait | unavailable
Completion event: TASK_EVENT
Wake states: DONE | FAILED | BLOCKED | NEEDS_APPROVAL
Progress notifications: disabled
Acceptance: <可验证结果>
Minimum test: <当前包或直接相关包命令>
~~~

共享文件、公共契约和严格写入使用该完整格式补充 owner、依赖和租约；普通任务不读取本节。

## 标准结果

~~~markdown
Status: DONE | PARTIAL | FAILED | BLOCKED | NEEDS_APPROVAL
Role: <角色>
Task: <task id>
Scope: <范围>
Changes: <实际变更>
Evidence: <绝对路径、符号或命令结果>
Verification: <最小验证及结果>
Skills requested: <selector + required/optional | none>
Skills loaded: <selector + source locator + STRICT_MODE version/SHA-256 | none>
Skills unavailable: <selector + reason | none>
Skill conflicts: <selector + conflict | none>
Unknowns: <未知项或 none>
Risks: <残余风险或 none>
Next action: <动作或 none>
~~~

任务每次进入 Task Brief 允许的 Wake state 后，向 Master 发送一次对应的 TASK_EVENT；同一状态不重复，不发送普通进度。只在确实需要继续工作时附加稳定 request_id 的 NEXT_TASK_REQUEST。

## 唤醒事件

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

同一状态只投递一次；重试保持 event_id 不变。状态变化可以产生新事件。完整日志、Diff 和会话历史不放入事件，通过 Result reference 按需读取。

## 严格租约

~~~markdown
Message type: AUTHORITY_LEASE
grant_id: <稳定 id>
source_master_thread_id: <真实 Master threadId>
target_thread_id: <真实 child threadId>
scope: <限定范围>
allowed_files: <绝对路径清单>
allowed_tests: <当前包命令>
expires_at: <截止时间>
forbidden_operations: <禁止动作>
Authorization: WRITE AUTHORIZED WITH SCOPED PACKAGE TESTS
Lease status: active
~~~

仅 STRICT_MODE 或用户明确要求时使用。

## 可选综合

用户要求综合或确实有多个结果需要合并时才使用：

~~~markdown
# Master Synthesis
Status: DONE | PARTIAL | BLOCKED
总体结论: <一句话>
会话结果: <threadId、任务、结果>
关键证据: <路径或命令>
未知项/风险: <none 或列表>
下一步: <责任人和动作>
~~~

没有综合需求时，Master 直接给出普通结果摘要，不等待所有会话或补齐模板字段。
