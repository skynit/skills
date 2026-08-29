---
name: review-code-plan
description: Review implementation plans before code changes. Use when the user asks Codex to assess a proposed coding plan, technical design, refactor plan, migration plan, bug-fix plan, rollout plan, or "how I will change the code" before implementation; also use when the user asks for risks, missing steps, feasibility, test scope, or architecture fit of a code-change plan.
---

# Review Code Plan

## Core stance

Act as a plan reviewer, not an implementer. Do not edit files or start implementing unless the user explicitly asks for changes after the review.

Prioritize bugs, hidden assumptions, missing validation, scope creep, and places where the plan conflicts with the existing codebase. Keep praise brief and secondary.

## Workflow

1. Read the proposed plan and any linked issue, spec, pasted notes, or relevant repository instructions.
2. Inspect the codebase enough to verify the plan's assumptions. Prefer `rg` / `rg --files` for discovery, then read the smallest useful set of files.
3. Evaluate whether the plan matches existing architecture, package boundaries, public APIs, data models, permissions, configuration, and test conventions.
4. Check operational risks: data migration, destructive behavior, concurrency, security, error handling, rollback, observability, platform differences, and dependency changes.
5. Check validation: current-package tests, targeted compile checks, manual verification steps, fixtures, mocks, and cases the plan omits.
6. If the plan is too vague to review, ask for the missing detail only when a reasonable assumption would be risky; otherwise state the assumption and continue.

## Review Criteria

Look for these issues first:

- The plan solves the wrong problem or misses part of the user-visible behavior.
- The plan contradicts existing code paths, naming, storage, lifecycle, or service boundaries.
- The plan relies on APIs, files, commands, environment variables, or external systems that do not exist or are not guaranteed.
- The plan changes shared contracts without updating callers, permissions, docs, migrations, tests, or defaults.
- The plan handles only the happy path and omits error states, cleanup, idempotency, retries, or partial failure behavior.
- The plan proposes broad refactors, new abstractions, or dependency changes without clear payoff.
- The planned test scope is too broad for the task or too narrow for the risk.

## Output Format

Lead with findings, ordered by severity. Use this shape:

```text
Findings
- [P1] Short title
  Evidence: file/path.go:123 or plan step name.
  Risk: What can break or remain incorrect.
  Suggested change: Concrete adjustment to the plan.

Open Questions
- Question only if it blocks a confident recommendation.

Verdict
Proceed / Revise / Block, with one sentence explaining why.
```

If there are no material issues, say so clearly, then mention residual risks or test gaps. Avoid long summaries unless the plan is complex.
