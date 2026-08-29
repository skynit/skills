---
name: portable-engineering-patterns
description: Use when bootstrapping, auditing, or refactoring a repository for agent-assisted development, or when writing cross-project AGENTS.md instructions, change-record or ADR policy, tool and sandbox boundaries, approval flows, and test gates. Distills the deepseek-harness four-plane engineering model into language- and stack-agnostic steps.
---

# Portable Engineering Patterns

Give a codebase a learnable, enforceable structure for human and agent contributors. This skill distills `deepseek-harness`; its source documents are cited by role rather than copied. This skill is guidance, not a universal checklist: adapt names, commands, and severities to the target project.

## Mental model

Agent-assisted engineering is four planes plus one meta-plane.

| Plane | Question it answers | Mechanism |
|---|---|---|
| Context | What must an agent know before touching code? | Root and subtree `AGENTS.md`, reference docs, skills |
| Record | Why does the code look like this, and what was given up? | Agent Notes/ADRs, commit and PR conventions, release notes |
| Boundary | What may an agent do, and what happens when it asks for more? | Capability seams, allowlists, scope layers, approval, sandbox, guards |
| Verification | How do we know a change did the intended thing and nothing else? | Focused unit tests, coverage, snapshots, real-endpoint e2e, CI matrix |
| Meta-governance | Who enforces the first four planes mechanically? | Generators, validators, git hooks, gate runner, branch protection |

Every durable rule should have exactly one home. Write the rule where it is owned; every other location links to that home. Prefer machine-checkable rules over prose reminders, and prefer narrow local checks over ritual full-suite runs.

## Operating procedure

1. **Inventory the repository.** Record the real build, test, run, release, and docs commands. List high-risk actions (shell, file writes, network, credentials, publish, deletion) and list the evidence tiers that already exist. Do not invent commands from memory.
2. **Bootstrap the context plane.** Write a root `AGENTS.md` of standing orders only: one-paragraph project identity, repository map, exact commands, secrets policy, change-record policy, execution boundaries, test policy, and a small number of non-obvious invariants. Keep each rule self-contained and one to three lines; link its full rationale. Add subtree `AGENTS.md` files only for local orders that do not belong at root. Create a docs `AGENTS.md` that fixes document placement, writing rules, and budgets. Symlink `CLAUDE.md` to the root file if you support Claude Code.
3. **Bootstrap the record plane.** Add an Agent Note/ADR directory with path-encoded lifecycle, class, and date. Require every non-trivial change to add or update one note in the same PR. Enforce the note skeleton mechanically: `Problem`, `Decision`, `Alternatives considered`, `Consequences` for implemented records; `Problem`, `Proposal`, `Acceptance criteria`, `Risks` for proposals. Keep implemented notes current with shipped reality; archive frozen snapshots instead of editing them. Adopt conventional commit prefixes and a rule that a commit body states the behavior, failure modes, and verification, not the reasoning transcript.
4. **Build the boundary plane.** Keep ordinary workspace actions default-allow and list them explicitly. Guard only high-risk effects: publish, deploy, credentials, system/service state, destructive data operations, and actions outside the workspace. Require approval for those actions, make grants one-shot and auditable, and fail closed only when the protected action cannot be authorized; missing policy must not block reading, editing, testing, or building. Add sandboxing or per-call limits only for untrusted input or demonstrated risk.
5. **Build the verification plane.** Give each behavior the cheapest test that would fail for its regression. Prefer the real implementation with only expensive or nondeterministic boundaries mocked. Assert external state or persisted logs, never the agent's self-report. Add keyless snapshots for stable model-visible or user-visible output and a with-key e2e smoke that self-skips without a secret. Put exhaustive coverage and the platform matrix in CI; keep pre-commit and pre-push hooks fast and narrowly scoped.
6. **Wire the meta-plane.** Turn each policy into an executable gate: markdown links, document budgets, type-equivalence pastes, generated catalogs, license notices, secret scan, workspace constraints. Encode gate dependencies in one runner so local and CI use the same graph. CI never writes expected outputs or repository state.
7. **Prove the loop once end-to-end.** Make one small sentinel change through the complete path: root and subtree instructions, Agent Note, focused test or snapshot, documentation update, hooks, and CI. Record what the sentinel taught and amend the AGENTS files in the same PR.
8. **Teach incrementally.** Point new contributors first at the commands and map, then at one cookbook, then at one Agent Note for rationale. Add a new standing rule only after a real violation or near-miss; otherwise link to the owning doc.

See [the full methodology](references/methodology.md) for the reproducible build order and the `deepseek-harness` source mapping. Copy the [root AGENTS.md template](references/templates/AGENTS.md), [subtree AGENTS.md template](references/templates/SUBTREE-AGENTS.md), [Agent Note template](references/templates/AGENT-NOTE.md), and [testing-policy template](references/templates/TESTING-POLICY.md) when bootstrapping.

## AGENTS.md authoring rules

- **Root carries standing orders only.** Every entry must be useful on every ordinary task. Stories, worked examples, and restated rationale do not belong there.
- **One fact, one home.** If a rule also lives in a reference, the root line becomes a link. A subtree rule never restates a repo-wide rule.
- **Commands are exact and owned.** Prefer package scripts or a single gate runner over paragraphs that can drift. State which checks are local and which CI owns.
- **Boundaries are stated as permissions and failure modes.** Name the default action, the escalation path, and what must never be bypassed.
- **Edit symlinks, not copies.** One real file at the root, symlinked into tool-specific names.
- **Enforce a budget and links.** Word ceilings, one-physical-line paragraphs, and relative Markdown links are cheap mechanical checks that prevent drift.
- **Delete before adding.** When a rule is added, search for an existing home or an obsolete rule to remove; condense when clarity survives.

## Change-record rules

- A commit records what changed and how it was verified. A change record explains why the decision stands and what lost.
- Encode status in the path (`proposed/`, `implemented/`, `rejected/`, or `archived/`) so inventory is a directory listing.
- Mandatory alternatives prevent re-litigation. Every implemented record must name what it beat and what it cost.
- The record is current-state truth, not a diary. Update names, paths, defaults, and mechanisms in the same change that moves them; never append history to an implemented record.
- Mechanical-only edits are the only exemption from the "one note per non-trivial change" rule.

## Boundary rules

- **Default allow ordinary development, guard only high-risk effects.** Reading code, editing the workspace, running focused tests/builds/lint, and local git operations are normal agent work; they must not require approval.
- **Reserve deny/ask for irreversible or external effects.** Require approval for publish, deploy, credential access, destructive data operations, system/service state changes, and actions outside the workspace; name the exact action and blast radius.
- **Use the smallest enforceable boundary.** Start with an explicit allowlist of normal commands and a short deny/ask list for high-risk actions. Add sandbox, per-call policy, or scope isolation only for untrusted input, multi-tenant use, or a demonstrated incident.
- **Fail closed only at the protected boundary.** If an approval, credential, or sandbox component is missing, block the protected high-risk action, never the surrounding development workflow.
- **Log for audit, not for ceremony.** Record high-risk actions, approvals, and model-visible inputs so they can be replayed; do not log every harmless read.

## Verification rules

- Match evidence to the surface: unit tests for behavior and races, snapshots for stable output, build/hygiene for published artifacts, real-endpoint e2e for providers.
- Run focused checks once locally; do not rerun a green check merely because a commit or push follows. CI owns the exhaustive matrix.
- Keyless tests keep contributors unblocked; a trusted CI lane with a required secret must fail loudly when the secret is missing instead of passing on skips.
- Never record or refresh expected outputs inside CI. Record locally, review every diff, then replay read-only in the gate.
- Coverage is necessary, not sufficient. An uncovered line is usually dead code or an untested contract, not an invitation to bolt on a tautological test.

## Report

When finished, report the planes added or changed, the exact commands run, any mechanical gate wired, and the first untested risk. Do not claim a check passed if the command was not executed.
