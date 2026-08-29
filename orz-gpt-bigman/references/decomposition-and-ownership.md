# 分解与所有权

仅在 STRICT_MODE、跨仓/跨进程、公共契约或实现与验收可分离时读取。目标是最少但足够的独立 owner，不以会话数量本身衡量质量。

## 分解门禁

首次 ASSIGN 前，Master 从真实计划、仓库边界和验收条件生成一份 `DECOMPOSITION_DECISION`。先识别可独立验收的产物，再决定会话；不能先选一个熟悉的助手，再把全部工作塞进它的 Scope。

满足以下两项时具备拆分条件：

1. 至少有两个可以分别定义输入、输出和验收标准的产物；
2. 这些产物具有不同仓库/包/进程写集，或可以通过已冻结的 API、schema、文件格式或计划决策解耦。

只有拆分能缩短关键路径、隔离仓库/权限/工具环境或提供验收要求的独立证据时才创建额外 thread。以下情况通常需要不同 owner：

- 两个独立仓库分别产生提交；
- 后端契约与前端 typed client 可以在契约冻结后独立实现；
- 实现和用户要求的独立 QA、真实环境验收或提交门禁；
- 数据迁移、运行时消费者和部署证明具有不同权限或环境；
- 一个 worker 需要加载超过两个直接相关 Skill 才能覆盖全部职责。

LIGHT_MODE 同时最多一个 active worker。STRICT_MODE 默认最多三个 ready owner；超过时必须记录具体收益、写集隔离和宿主容量证据，且不得超过宿主工具上限。

## 默认执行图

跨仓纵向切片默认使用最小执行图：

```text
contract owner（仅在契约尚未冻结时）
        |
        +-- repository/package owner A
        +-- repository/package owner B
                    |
             independent validator
```

- 契约已经由锁定计划、schema 或文档冻结时，独立 owner 可直接并行。
- 契约尚未冻结时，先把“冻结契约”作为一个有界任务完成；收到 DONE 后再分派下游，不增加新的非终态事件类型。
- 同一 checkout 的重叠写集必须串行，或使用相互隔离的 worktree；不同仓库或明确不重叠写集才可并行写入。
- 集成测试依赖所有实现产物时，由独立 validator 在 owner DONE 后执行。validator 只验证，不修复、不提交实现。
- 每个 owner 只接收自己的仓库/包、写集、依赖、验收和最小测试；不得承担未登记的相邻产物。

## 单 worker 例外

已经满足拆分收益门禁后，只有以下原因可以退回单 worker：

- 产物共享不可拆分的事务、迁移或原子提交边界；
- 写集高度重叠，隔离 worktree 仍不能避免语义冲突；
- 拆分会在未冻结契约上制造双重事实来源，且当前阶段本身就是契约冻结任务；
- 宿主真实返回容量、创建失败或工具不可用，无法取得必要的独立 thread。

例外必须写入 `Single-worker exception`，包含事实证据和降级后的风险。已有助手熟悉上下文、先前做过相邻阶段、希望减少 token 或会话、以及“纵向切片 owner”标签都不是充分理由。

## 收敛规则

- Master 只在依赖事件到达后分派下游，不轮询未完成 owner。
- 任一 owner FAILED/BLOCKED/NEEDS_APPROVAL 时，只暂停依赖它的任务；无依赖 owner 可继续。
- validator 发现问题后发送 FAILED 或 BLOCKED，由 Master 决定把修复交回原 owner；validator 不越权修改。
- 所有要求的 owner 结果和独立验证齐全后，Master 才综合、提交或报告完成。
