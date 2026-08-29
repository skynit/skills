# 上下文与压缩

仅在准备压缩、上下文接近宿主限制、跨阶段复用会话或压缩后恢复时读取。目标是先保存足以继续工作的事实，再由宿主能力决定是否主动压缩。

## 触发条件

满足任一条件时评估压缩：

- 宿主提供上下文占用信号且已达到约 70%–80%；
- 一个批次或重大阶段刚完成，后续工作不再需要原始过程；
- 大段日志、搜索结果或讨论已经收敛为稳定结论和结果引用；
- 已完成的 worker 将继续处理同一或紧邻领域，但当前历史中已收敛的过程明显多于后续仍需的事实。

不要按固定时间或消息数压缩。worker 有 active turn、Master 有未处理 TASK_EVENT、审批或公共契约尚未决、关键证据仍只存在于聊天时不得压缩。

压缩不能把不相关上下文变成复用收益。新任务与 worker 最近职责领域明显不同时，优先创建新 thread；只有领域相同或紧邻、保留事实仍有直接价值时，才在 checkpoint 后压缩并复用。

## 确定性 checkpoint

需要跨 turn 恢复时，状态文件固定为：

```text
<project>/.agent_tmp/orz-gpt-bigman/<master-thread-id>.json
```

写入前必须确认 `.agent_tmp/` 已被 Git 忽略；不满足时不创建 ledger，也不声称可持久恢复。不得扫描整个 `.agent_tmp/` 猜测状态文件。

压缩前使用 `orz_state.py checkpoint` 保存 ledger revision、时间、原因、事件游标、task 数量和唯一下一动作，再运行 `verify`。完整 task 契约只保存在 `ledger.tasks`，checkpoint 不复制第二份任务事实。后续任一状态变更都会提高 revision，使 `resume.checkpoint_current` 变为 false；过期 checkpoint 的 `next_action` 仅是历史记录，不得执行。`PENDING_DISPATCH`、`ASSIGNED`、`IN_PROGRESS`、`NEEDS_APPROVAL` 或未消费 TASK_EVENT 仍存在时，脚本拒绝 checkpoint。

## 执行与恢复

- 宿主明确暴露线程压缩工具时，checkpoint 和 verify 成功后才调用；不要假设工具存在。
- 宿主未暴露主动压缩时，只记录已就绪 checkpoint，等待宿主自动压缩。
- Master 可在所有 active owner 都处于 `WAITING_EVENT` 后压缩；worker 只在完成交接或两项任务之间压缩。
- 恢复后先用确定性路径执行一次 `resume`；默认返回未关闭 task，并在 `resolved_dependencies` 中附带这些 task 实际引用的 CLOSED 依赖终态和结果引用，确需全部历史时使用 `--include-closed`。只有 `checkpoint_current: true` 时才采用 checkpoint 的唯一下一动作，否则根据当前 task 做一次真实状态 reconciliation；不要重复 list/read/wait。
