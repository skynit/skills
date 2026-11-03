---
name: handoff
description: Compact the current conversation into a handoff document for another
  agent to pick up.
metadata:
  source-repository: mattpocock/skills
  source-commit: 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d
  local-adaptation: Codex invocation and project authorization conventions
---

在 Codex 中，文中的 Skill tool 调用表示读取并遵循可用技能列表中对应的 `SKILL.md`；沿用其调用策略和当前任务授权。


Write a handoff document summarising the current conversation so a fresh agent can continue the work. Save to the temporary directory of the user's OS (`$TMPDIR`, else `/tmp`; `%TEMP%` on Windows) - not the current workspace.

Include a "suggested skills" section in the document, naming which skills the next agent should call the Skill tool for.

Do not duplicate content already captured in other artifacts (specs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.

Redact any sensitive information, such as API keys, passwords, or personally identifiable information.

If the user passed arguments, treat them as a description of what the next session will focus on and tailor the doc accordingly.
