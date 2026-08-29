# Portable methodology

This reference is the step-by-step reproduction path behind [the skill](../SKILL.md). Each stage is independently useful: stop at any stage and the repository is still coherent.

## Source mapping

`deepseek-harness` demonstrates every plane in one repository.

| Plane | DeepSeek Harness mechanism | Portable equivalent |
|---|---|---|
| Context | Root `AGENTS.md` standing orders; subtree `packages/AGENTS.md`, `examples/AGENTS.md`, `docs/AGENTS.md`; `docs/architecture.md`, `docs/testing.md`; `.agents/skills/**/SKILL.md` | Root and subtree instruction files plus a tiered doc tree |
| Record | `.agents/notes/{proposed,implemented,rejected}/{class}/yyyy-mm-dd-topic.md` with a fixed skeleton; conventional commits; PR kind/area labels; release commits | ADR directory with path-encoded status, a validator, and commit conventions |
| Boundary | Plugin capability seams; scoped registries; `tools/pre-execute` allow/deny/ask waterfall; closed approval outcomes; `read-only`/`workspace-write`/`danger-full-access` sandbox modes; tool timeouts and loop guards; model-visible means logged | A small interface per dangerous capability, default-deny policy, one-shot grants, per-call confinement |
| Verification | Unit tests, per-file 100% coverage gate, keyless snapshots, with-key e2e that self-skips, web snapshots, artifact/hygiene gates | A test-tier contract plus evidence selection rules |
| Meta-governance | `scripts/run-gates.ts` dependency graph; lefthook pre-commit/pre-push; generated catalogs; doc budgets and link checks; CI lanes | Gate runner, narrow hooks, exhaustive CI, freshness checks |

The portable model keeps the same relationships while allowing any language, build tool, and issue tracker.

## Stage 0: inventory

Collect facts before writing rules.

- Run the actual install, test, build, lint, start, and release commands once.
- Draw a repository map: source roots, package boundaries, generated directories, deployment configs, secrets, on-disk and wire formats.
- List every action an agent might take and classify it as read-only, workspace write, external effect, credential touch, or irreversible publish.
- List current evidence: unit tests, integration tests, manual checks, snapshots, CI jobs.
- Record the gaps: which behavior has no test, which rule is only in someone's memory, which generated file is hand-edited.

## Stage 1: context plane

Create in this order.

1. `AGENTS.md` at the repository root. Use [the template](templates/AGENTS.md). Keep it under a word budget.
2. One subtree `AGENTS.md` per large directory that has local authoring rules. Use [the subtree template](templates/SUBTREE-AGENTS.md).
3. `docs/AGENTS.md` describing document tiers, reference versus tutorial, writing rules, and budgets.
4. `docs/architecture.md` as the ordered map agents must read before changing source.
5. `docs/testing.md` as the single home for test policy.
6. One cookbook per repeated procedure, with numbered verification steps.
7. Symlinks or compatibility files such as `CLAUDE.md -> AGENTS.md`.

Authoring order for every doc: locate its tier, set its permitted detail, choose tutorial or reference, order concepts by prerequisite, then write. Every fact has one home; elsewhere link.

## Stage 2: record plane

1. Create `.agents/notes/{proposed,implemented,rejected}/<class>/`. Use classes such as `feature`, `bug-fix`, `simplification`, `architecture`, `process`, and `testing`.
2. Adopt the [Agent Note template](templates/AGENT-NOTE.md). The first two lines are machine-checked: title, then `Status:`.
3. Write a small validator that checks path classes, status/path agreement, the implemented skeleton, and mandatory `Alternatives considered`. Add it to the project gate runner.
4. Adopt commit conventions: a short conventional prefix such as `feat(scope):`, `fix(scope):`, `docs:`, `test:`, `refactor:`, `ci:`, `release:`. For non-trivial commits, the body states current behavior after the change, failure modes, and verification. Delete reasoning transcripts before committing.
5. Adopt PR rules: one material change per PR, split independent changes, label all material areas, do not merge before the selected checks pass. Prefer review on the introducing PR rather than propagating a known defect.
6. Release by committing version bumps and tags from the repository; CI publishes but does not invent versions or edit the repo.

Lifecycle rules: a proposal moves to `implemented/` by rewriting plans into present-tense shipped facts; a completed decision that no longer guides future work moves to a frozen `archived/` tree with no body edits. Never edit an archived record.

## Stage 3: boundary plane

Classify before restricting. Boundaries protect high-risk effects; they must not turn normal development into a permission maze.

1. Inventory actions and assign risk tiers: ordinary workspace actions (read, edit, focused test/build/lint, local git), external effects (network, services, credentials), and irreversible effects (publish, deploy, delete user data).
2. Keep ordinary workspace actions default-allow. State the allowlist once in `AGENTS.md`; do not add per-action approval or sandbox to them.
3. Guard only high-risk actions with a short deny/ask list. Require approval for publish, deploy, credential access, system/service state changes, and operations outside the workspace; name the exact action and blast radius.
4. Add a real enforcement seam only when a high-risk capability needs one: model tools, credentials, publish, or untrusted execution. Service/provider/consumer roles and pre/post pipelines are for that boundary, not for every command the agent runs.
5. Fail closed at the protected boundary only. A missing approval answerer or credential gate blocks the protected action; it must not block reading, editing, testing, or building.
6. Use sandboxing and per-call policy when the runtime executes untrusted or model-generated input, or when one incident proves a class of risk. A trusted contributor agent in its own workspace normally runs commands directly.
7. Bound expensive or externally-observable operations with deadlines and limits; do not wrap every local command in a timeout.
8. Scrub secrets from spawned environments and logs. Record high-risk actions and approvals for audit; skip logging harmless reads.

## Stage 4: verification plane

1. Write a testing-policy doc from [the template](templates/TESTING-POLICY.md).
2. Keep unit tests beside the behavior. Add contract-regression tests whenever a bug class is found.
3. Add a coverage gate only after unit tests exist. A per-file high bar finds dead code; it does not prove product behavior.
4. Add keyless snapshot or golden-output tests for stable model-facing, CLI, API, or UI output. Record locally and review diffs as behavior changes.
5. Add with-key e2e smokes for live providers. Suites self-skip without a secret so keyless contributors and CI stay unblocked; a trusted lane that must have the secret fails a preflight when it is absent.
6. Assert the world, not the self-report: reread files, inspect persisted logs, and check untouched files byte-for-byte. Boot through the real entry path, not a hand-mounted fixture.
7. Mock only the expensive or nondeterministic boundary. Everything downstream of the mock remains real.

## Stage 5: meta-governance

1. Use git hooks only for fast local checkpoints: staged whitespace, staged lint, generated-notice freshness, a scoped format check, and a cheap typecheck.
2. Build one gate runner that encodes command dependencies and concurrency. Both local rehearsal and CI call the same definitions.
3. Move exhaustive coverage, platform matrix, built-artifact smokes, browser or native snapshots, and real-API runs into CI lanes.
4. Make CI read-only: it replays expected outputs, never records them. Secrets are available only to trusted events, never `pull_request_target` for fork code.
5. Prefer generators over hand-maintained catalogs: type docs, config catalogs, dependency graphs, and license notices regenerate from source and fail when stale.
6. Add document checks: relative links resolve, budgets hold, prose paragraphs are one physical line, and generated doc fences match source.

## Sentinel change

After wiring the planes, make one small end-to-end change and treat it as the first lesson.

- Pick a change with one behavior, one test, and one doc surface.
- Follow every instruction file and record every decision.
- Let the agent run the selected checks exactly once and report the actual commands.
- If a rule was ambiguous, edit the owning `AGENTS.md` in the same change instead of leaving tribal knowledge.
- Review the PR as if you were a new maintainer and delete every instruction that did not affect the outcome.

## Adoption order for an existing repository

1. Add root `AGENTS.md` and `docs/testing.md`; run the sentinel change.
2. Add Agent Notes and the format validator; apply to the next non-trivial change.
3. Add one boundary gate for the highest-risk action; migrate that action behind it.
4. Add snapshot or e2e coverage for the most recently broken behavior.
5. Add doc budgets and generated catalogs after the doc tree stabilizes.
6. Enforce CI lanes and branch protection last, when local evidence is already trusted.

Adopt incrementally. A complete governance stack without one real change passing through it is architecture, not engineering.
