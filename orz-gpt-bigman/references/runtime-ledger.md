# 确定性运行时 ledger

`scripts/orz_state.py` 是一个零第三方依赖的本地状态工具。schema v4 管理异步分派、真实 thread 绑定、结构化 Skill binding、依赖、等待 cursor、失联状态、事件消费、revision checkpoint 和 `TASK_EVENT` 去重；它不创建 thread、不发送消息、不执行 shell，也不决定权限。旧 schema 不自动迁移，读取时明确 fail closed。

## 使用前门禁

1. 状态文件固定为 `<project>/.agent_tmp/orz-gpt-bigman/<master-thread-id>.json`，并以绝对路径传给 `--state-file`。
2. 写入前在目标项目根目录确认 `.agent_tmp/` 满足 `git check-ignore -q`；未忽略时不要写入。
3. 不把 ledger 放进仓库根目录，不把完整日志、Diff 或密钥写进 ledger。
4. 状态文件和伴随 lock 文件由脚本设置为 `0600`；原子替换避免半写入。

## 生命周期

```text
init -> reserve(PENDING_DISPATCH) -> bind(ASSIGNED)
     or register(ASSIGNED)
     -> transition(IN_PROGRESS -> WAITING_EVENT)
     -> optional stalled(STALLED) -> transition(IN_PROGRESS or WAITING_EVENT)
     -> skill-result(required/optional selector evidence)
     -> event(DONE | FAILED | BLOCKED | NEEDS_APPROVAL)
     -> consume-event
     -> optional transition(IN_PROGRESS) -> event(new state)
     -> transition(CLOSED)
```

`clientThreadId` 只能进入 `PENDING_DISPATCH`；取得真实 `threadId` 和 `hostId` 后才能 bind。依赖未成功时不能进入 `IN_PROGRESS`。Required Skill 没有目标线程的 loaded 证据时不能记录 DONE。`NEEDS_APPROVAL` 到 `DONE` 是合法状态变化；每次状态变化使用新的事件序号，同一事件重试使用相同 `event_id`。脚本拒绝非法迁移、冲突重复事件、悬空事件和不连续序号。

## 常用命令

```bash
STATE=/absolute/project/.agent_tmp/orz-gpt-bigman/019master.json
python scripts/orz_state.py --state-file "$STATE" init \
  --batch-id batch-001 --master-thread-id <master-thread-id> \
  --objective "完成可验证的目标"
python scripts/orz_state.py --state-file "$STATE" register \
  --task-id inspect-api --thread-id 019abc --host-id host-1 \
  --role explorer --project /absolute/project --model configured-default \
  --scope /absolute/project/package --acceptance "当前包验证通过" --mode STRICT_MODE \
  --required-skill 'openai-docs::核对官方文档'
python scripts/orz_state.py --state-file "$STATE" transition \
  --task-id inspect-api --to IN_PROGRESS --reason dispatch-accepted
python scripts/orz_state.py --state-file "$STATE" skill-result \
  --task-id inspect-api --selector openai-docs --available yes --loaded yes \
  --source-locator /resolved/openai-docs/SKILL.md --frontmatter-name openai-docs \
  --source-version openai-docs@installed-version
python scripts/orz_state.py --state-file "$STATE" event \
  --task-id inspect-api --state DONE --result-reference /absolute/result.md
python scripts/orz_state.py --state-file "$STATE" consume-event \
  --event-id 019abc:inspect-api:DONE:1
python scripts/orz_state.py --state-file "$STATE" transition \
  --task-id inspect-api --to CLOSED --reason event-consumed
python scripts/orz_state.py --state-file "$STATE" thread-lifecycle-ready \
  --thread-id 019abc --host-status idle
python scripts/orz_state.py --state-file "$STATE" verify
python scripts/orz_state.py --state-file "$STATE" status
```

异步创建先用 `reserve --client-thread-id ...`，恢复取得真实身份后使用 `bind --thread-id ... --host-id ...`；创建明确失败且没有真实 threadId 时使用 `dispatch-failed --error-reference ...`，不得伪造 TASK_EVENT。Skill 参数使用 `SELECTOR::PURPOSE`，分别通过 `--required-skill` 和 `--optional-skill` 登记。worker 交接后用 `skill-result` 写入 available、loaded、source locator 和 frontmatter name；STRICT_MODE 还必须写入 `--source-version` 或 `--content-digest`。使用 digest 时 source locator 必须是 Master 可读取的绝对本地文件，脚本会重新计算 SHA-256 后再记录；selector 不从路径或 frontmatter 推导。

TASK_EVENT 必须先 `consume-event`，再把终态 task 转为 `CLOSED`。复用前把 list/read 获得的真实宿主状态传给 `thread-lifecycle-ready`；仅 `idle`/`notLoaded`、所有旧 task 已 `CLOSED` 且该 thread 无未消费事件时返回 `lifecycle_ready: true`。这只是生命周期门槛，角色、项目、模型和领域匹配仍由 Master 判断。

有界等待超时时，将 `afterCursor` 和 deadline 写入 `transition --to WAITING_EVENT`；deadline 已过时用 `stalled`，不能直接伪造失败。Master 处理 TASK_EVENT 后按顺序执行 `consume-event`；未消费事件存在时 checkpoint 必须失败。

准备压缩时运行 `checkpoint --reason ... --next-action ...` 后再 `verify`。checkpoint 记录 ledger revision；后续变更会让 `resume.checkpoint_current` 变为 false。`resume` 默认只返回未关闭 task、closed 数量及这些 task 引用的 `resolved_dependencies`；`resume --include-closed` 才返回完整历史。详细门禁见 [上下文与压缩](context-management.md)。

Task Brief 中的真实 `threadId`、`hostId`、角色、项目和模型必须先由 Codex app 工具确认；ledger 不能用 title、preview、`agent_id` 或模型猜测替代这些字段。
