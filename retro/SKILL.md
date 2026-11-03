---
name: retro
description: Conduct a retrospective on a coding session.
metadata:
  source-repository: mattpocock/skills
  source-commit: 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d
  local-adaptation: Codex invocation and project authorization conventions
---

在 Codex 中，文中的 Skill tool 调用表示读取并遵循可用技能列表中对应的 `SKILL.md`；沿用其调用策略和当前任务授权。


The user has asked for a **retrospective**. You are suggesting improvements to the coding agent's **environment** to improve future runs.

## Steps

1. Call the Skill tool with `writing-for-agents` for the writing style guide.

2. Read the primary sources for the session the user specifies. This may mean searching through session logs on this machine. If the user doesn't specify a session, default to the current one.

3. Look for candidates for improvement in these categories.

- **Navigation**: how easy was it for the agent to find the right files? Are there hidden dependencies between files? Would a **navigation pointer** make it easier? _Use when_ the session took a long time to find a piece of information.
- **Automated checks**: are there automated checks that could catch errors the agent made? Linting, typing, tests, filesystem linters? Read the repo's own check command first (its `package.json`/build-tool `lint`/`check` scripts, its CI workflow), so a check that already exists but sits unwired or silently broken is the finding, not a reinvention. A repo with no **guardrail** (no pre-commit hook and no CI job running its lint/typecheck/test command) is itself a finding: an un-linted repo is a standing missed opportunity, not a neutral default. _Use when_ the agent made a mistake an automated check could have caught, or the repo has no guardrail at all.
- **Coding standards**: should the **reviewer agent** be given a new rule to enforce? Should an existing rule be removed or clarified? Classify the violation first: a **mechanical** one (a fixed syntactic pattern, a banned API, an import shape, a file-location rule) gets a deterministic check, full stop: a custom rule in the repo's own linter, a new pre-commit hook, or a new CI job, whichever the repo's language and existing guardrail make cheapest. Recommend a deterministic check for mechanical violations; implement it only within the authorized task scope. Keep judgement rules in the project's existing authoritative instructions. For CW, use the nearest applicable `AGENTS.md`, with confirmed cause, verification evidence, and reading conditions. _Use when_ the reviewer agent failed to catch a mistake.
- **Global AGENTS.md**: are any instructions better placed in a scoped `AGENTS.md`, an existing reference, or an automated check while preserving the project's single authoritative location? _Use when_ the AGENTS.md file is particularly large - in the repo OR the user's global scope.
- **Tool economy**: did the agent make expensive tool calls that could be streamlined? Is there any custom tooling (CLI's, MCP's) that is particularly token-inefficient? _Use when_ the agent made an expensive tool call.
- **No-ops**: look for instructions in steering files that don't modify the agent's behavior. _Use when_ the steering files are large and unwieldy.
- **Information access**: look for opportunities to increase the agent's access to information. Teeing dev server logs, readonly access to third-party services. _Use when_ a crucial piece of information was not available to the agent.

4. Present these candidates to the user, in order of severity.

## Reference

### Implementation vs Review

Remember that all work goes through two stages: implementation and review. The implementation agent has the most **context pressure**. They are responsible for exploration, writing code, and debugging failures.

The review agent has the least context pressure - it receives a diff, so no exploration needed. It often does not need to write code or debug.

Both implementation and review agents follow applicable project rules. Review adds an independent check; it does not transfer correctness obligations away from implementation.

### Files

You have access to several files in the repo:

- `CLAUDE.md`/`AGENTS.md`: read the applicable files for the task scope. Preserve their role as the authoritative home of collaboration rules; use clear navigation pointers for material read only under specific conditions.
- `CODING_STANDARDS.md`: use this only where the project already designates it as authoritative. In CW, collaboration rules belong in the applicable `AGENTS.md`; avoid creating a competing rules document.
- Docs: use docs as references files, pointed to by other files. Look for existing docs before writing new ones.
- Skills: use skills for docs (since their description goes into the agent's context window), or for user-invoked commands. Follow the advice in the `writing-for-agents` skill.
