---
name: submit-upstream-pr
description: 整理代码并向项目对应的远程主仓库提交或更新 PR。用户要求“提交 PR”“把修复提交上去”“整理 PR”“向上游提 PR”时使用。自动核对 fork 与上游关系；问题、诊断报告、截图和验证说明放在 PR 描述，不作为报告文件提交到源码仓库。
---

# 向正确的项目主仓库提交 PR

## 用户约定

1. PR 的目标是当前项目对应的远程主仓库，不能因为 `origin` 指向自己的 fork，就把 PR 提到自己的 fork。
2. 自己的 fork 只用于承载 head 分支和推送代码。跨仓库 PR 应是 `主仓库:base ← 自己的 fork:head`。
3. 源码提交只包含实现所需的代码、测试和必要的正常项目文档。问题记录、排查过程、审查报告、诊断报告、临时探针、日志、对比截图及生成报告不进入源码提交。
4. 问题、报告、复现步骤、风险、验证结果和对比图只用于 PR 描述。不要为了在描述里显示图片而把图片提交到仓库。
5. 用户授权提交 PR 后，完成范围内的实现、验证、提交、推送和 PR 创建或更新；无需再次请求同一项授权。不得自行合并 PR、修改主分支保护或重写主分支历史。

用户的明确指令优先于本技能默认约定；只有明确要求将某份报告或图片作为正式项目资产提交时，才将其纳入提交。

## 1. 确认项目和远程目标

先读取当前工作目录、工作区规则、Git 状态、分支和远程信息。不要把运行环境中的工具实现仓库当成当前项目。

```bash
pwd
git status --short
git branch --show-current
git remote -v
gh repo view --json nameWithOwner,isFork,parent,defaultBranchRef
```

通过 GitHub API 核对远程 fork 的父仓库：

```bash
gh api repos/OWNER/REPO --jq '{full_name,fork,parent:.parent.full_name,source:.source.full_name,default_branch}'
```

- `origin` 是 fork：默认以其直接父仓库为 PR 目标，并核对现有 `upstream` remote。不要盲目跳到 fork 链最顶端的 `source`；直接父仓库通常才是项目维护者所在的主仓库。
- `origin` 不是 fork：以对应项目仓库为候选目标，核对用户指定的仓库和现有远程信息。
- 不依赖 README 徽章、仓库名称或账户所有权猜测目标。
- 远程信息冲突、存在多个合理的上游或用户明确指定了不同仓库时，先完成可独立进行的准备工作，再仅询问缺失的目标信息。

确定后使用明确的 `--repo OWNER/REPO`、`--base BASE` 和 `--head FORK_OWNER:BRANCH`，避免 GitHub CLI 自动选错仓库。

## 2. 隔离已有工作并确定范围

- 记录已有未提交改动，不覆盖、不暂存、不提交他人的工作。
- 有无关改动时，在许可目录内创建独立 worktree。不要自动 stash 用户工作。
- 获取最新目标 base，围绕当前需求创建分支。不要直接从含无关提交的 fork `main` 创建 PR。
- 核对待提交文件和提交列表：

```bash
git diff --name-status TARGET_BASE...HEAD
git log --oneline TARGET_BASE..HEAD
```

准备阶段尚未提交的修改另用 `git diff` 与 `git diff --cached` 检查。

排除临时目录、报告、截图、日志、构建产物、凭证和无关版本号变更。使用明确文件路径暂存，不使用会顺带纳入无关改动的 `git add -A`。

## 3. 实现与验证

- 先定位原因，再实现最小必要修正，不把猜测包装成已确认根因。
- 普通浏览器模拟结果不能代替 Android WebView 或真机验证。
- 对实现运行适当的编译、测试和仓库规定的检查；有 i18n、lint、格式或配置门禁时一并运行相关项。
- 检查每条命令的真实退出状态；使用管道时启用 `pipefail`，不要用 `tail` 的成功覆盖构建失败。
- 缺设备、依赖或运行环境时准确记录未验证项，不宣称“修复已验收”。不要为了通过检查而全局放宽规则。
- 不反复扩大验证范围；已有有效结果在相关代码未变化时可以复用。

提交前检查：

```bash
git diff --check
git diff --cached --name-status
git diff --cached
```

## 4. 把问题与报告放在 PR 描述

PR 描述面向没有读过聊天记录的维护者，围绕最终实现重写，不复制完整排查流水。

建议包含：

- **问题与触发条件**：用户遇到什么，如何复现。
- **修改后的行为**：代码改了什么，为什么这样改。
- **证据与对比**：已观察的事实、推测和待确认项明确区分。
- **验证**：实际运行的命令和结果，尚未完成的真机或平台验证。
- **风险**：与本次变更相关的限制和回归关注点。

### 图片与附件

- 默认不提交图片到仓库，也不建立只用来托管报告图片的分支。
- 有可用且已授权的 GitHub 附件上传能力时，上传为 PR 附件并嵌入描述。
- 无上传能力时完成代码 PR，在说明中如实列出待手动添加的附件；不要伪造链接或改用仓库提交托管。
- 不将浏览器对照截图称作真机修复后截图。
- 用户撤回图片或报告时，移除当前 PR 描述中的对应内容；删除仓库当前版本的文件不代表抹除 Git 历史，不擅自重写历史。

将多行描述写到仓库之外的临时文件，通过 `--body-file` 提交，保留真实换行并避免 shell 插值。

## 5. 提交到正确上游

推送实现分支至自己有权限的 fork，然后明确创建跨仓库 PR：

```bash
git push -u FORK_REMOTE HEAD:HEAD_BRANCH
gh pr create --repo UPSTREAM_OWNER/REPO --base BASE_BRANCH --head FORK_OWNER:HEAD_BRANCH --title '描述最终修复的标题' --body-file /absolute/path/to/pr-body.md
```

命令中的 remote、owner、repo、分支和描述路径必须替换为已核验的实际值。

创建前先查找已有 PR：

- **OPEN**：往其 head 分支追加相关修正，更新标题和描述，不重复创建。
- **MERGED / CLOSED**：不要把追加到旧 head 的提交当作已进入原 PR。以最新上游 base 创建新分支和新 PR，只带需要继续提交的变更。
- 上游已经删除或重组的报告和资产，不作为修复顺手重新引入。
- 网络或 SSH 配置异常时，仅对本次命令使用适当的连接设置；不要擅改系统 SSH 配置或扩大文件权限。
- 如需对自己的 head 分支重整历史，先核对远端状态，使用 `--force-with-lease`；默认追加提交，不强推主分支。

## 6. 核验远端结果与 CI

提交或更新后，读取 PR 元数据，核对：

```bash
gh pr view PR_NUMBER --repo UPSTREAM_OWNER/REPO --json url,state,baseRefName,headRefName,headRepositoryOwner,headRefOid,files,commits
gh pr checks PR_NUMBER --repo UPSTREAM_OWNER/REPO
```

确认目标仓库、base、head 所有者、最新 SHA 和文件列表均符合预期；注意 API 可能短暂延迟，不能把旧 SHA 当作新提交的结果。

CI 失败时读取确切 job 日志，在 head 分支复现并最小修正，再推送到同一开放 PR。区分“本地通过”“远端 CI 通过”和“仍在运行”。

## 7. 交付

最终简洁说明：

- 主仓库 PR 链接。
- 本次实现及提交范围。
- 实际通过的验证、远端 CI 状态与待验证项。
- 有无未完成的附件上传。

清理自己创建的临时 worktree 和后台任务，不清理用户或其他会话的文件。不合并 PR，不对用户无关工作进行同步或重置。
