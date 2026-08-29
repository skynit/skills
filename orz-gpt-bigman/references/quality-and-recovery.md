# 质量与恢复

仅在用户要求 QA/Reviewer、任务进入 STRICT_MODE、出现冲突或需要恢复时读取。

## 模式

- LIGHT_MODE 是默认：不强制独立 QA、Reviewer、validator、依赖门或批次验收。Master 依据最小命令和实际证据收敛。
- STRICT_MODE 只用于安全、公共契约、schema/迁移、跨进程、破坏性操作、发布、冲突或用户明确要求。按 [分解与所有权](decomposition-and-ownership.md) 启用最少但足够的实现 owner，并只启用与风险直接相关的 validator 或 Reviewer，避免无关会话。
- 低风险任务不因没有 QA/Reviewer 而阻塞；严格任务也不自动扩展到全仓测试。

## QA 与 Reviewer

- QA 触发条件：用户明确要求、严格路径、高风险变更、失败重试前或需要独立验证的具体争议。
- Reviewer 触发条件：用户明确要求方向审核、存在重大范围/授权漂移或 Master 请求一次 material review。普通分派、等待和完成不触发。
- 每次只启动一个直接相关的 QA 或 Reviewer；已有最终结果就复用，不重复唤醒。
- Reviewer 只读，不修改文件；QA 只验证，不代替 Dev 修复。普通轻量任务不需要发送 MASTER_DIRECTION_REVIEW。
- STRICT_MODE 的验收条件包含真实数据库/设备/浏览器/跨进程联调、独立 QA 或提交门禁时，实施 owner 不能作为唯一 validator；所有实现 owner DONE 后必须由另一个真实 `CODEX_THREAD` 验证。validator 缺失时由 Master 创建，不得把独立证明降级为实施者自证。

## 冲突

- Dev 与 QA 结论冲突时，先运行一个最小、可复现的当前包命令；以真实 Stdout/Stderr 为准。
- 命令无法裁决且需要用户决定时标记 `NEEDS_APPROVAL`；缺少外部事实且用户也无法直接裁决时标记 `BLOCKED`，不用多数意见强行通过。
- 不把静态 quick_validate.py 当成运行时行为证明。

## 恢复与临时材料

- 普通恢复不扫描 `.agent_tmp/`。已启用 ledger 时，只读取 [上下文与压缩](context-management.md) 定义的确定性状态文件。
- 只有事件明确通知 `.agent_tmp/PLAN.md` 已更新且文件存在时，才额外按需只读该计划文件。
- 实际使用 .agent_tmp/ 前确认 git check-ignore -q .agent_tmp/；未忽略时禁止写入。

## 回滚

- 只有实际产生破坏性影响、用户明确授权，或用户要求恢复时才回滚。
- 回滚前记录目标、git status 和可恢复证据；禁止未经授权的 git reset --hard、强推或历史改写。
- 普通验证失败只修正当前范围或报告 blocker，不触发两次 QA 拒绝、级联回滚等额外流程。

## 完成

- 轻量任务：结果、证据和最小验证齐全即可完成。
- 严格任务：只检查与风险直接相关的授权、验证和审核项；不要求完整会话清单或统一综合模板。
