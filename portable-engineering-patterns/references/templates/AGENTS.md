# AGENTS.md

`<PROJECT>` is `<one-sentence product definition>`. Read `docs/architecture.md` before changing `<source roots>`; follow `docs/AGENTS.md` for documentation.

## Repository map

```
src/           Product source
tests/         Test suites beside or mirroring src
docs/          Architecture, testing policy, cookbooks
.agents/       Agent Notes, skills, and agent workflows
scripts/       Gates and generators
.github/       CI workflows
```

Add the directories that matter for your project; delete this table if the tree is self-evident.

## Commands

```sh
<install>            # install pinned dependencies
<test>               # focused unit and integration tests
<test:coverage>      # CI coverage gate
<test:snapshot>      # keyless expected-output tests
<test:snapshot:record> # re-record expected outputs locally
<test:e2e>           # real-provider tests; self-skip without <SECRET>
<typecheck>          # static type and contract checks
<lint>               # lint the source
<build>              # build shipped artifacts
<check:local>        # narrow relevant local gates
<check:ci>           # exhaustive CI gate set
<start>              # run the product from source
```

Keep this list exact. Own the inventory in `package.json`, `Makefile`, or a script; do not restate it elsewhere.

## Secrets and host failures

Real-provider tests read `<SECRET>` from the environment or a gitignored `.env`. Never commit credentials. CI self-skips without a secret; a trusted lane that must have one fails loudly if it is absent.

When a command fails inside an agent sandbox or runner, retry unchanged with the narrowest host escalation before diagnosing the project. Require evidence for the sandbox failure; never bypass a genuine test failure or a product security boundary.

## Change record

Every non-trivial change adds or updates one Agent Note under `.agents/notes/` in the same PR. Use conventional commit prefixes; a commit body states the shipped behavior, failure modes, and verification, not the reasoning transcript.

## Execution boundaries

Agents may read, edit, test, build, and run local git operations inside the workspace without approval. The command table above is the normal-action allowlist.

Only irreversible or external effects require approval: publish, deploy, credential access, system/service state changes, destructive data operations, and actions outside the workspace. Grants are one-shot and audited, and a missing policy component blocks only the protected action. Apply timeouts and sandboxing when executing untrusted or model-generated input.

## Testing policy

Use `docs/testing.md` as the one home. Match evidence to the surface: focused tests for behavior, snapshots for stable model or user output, build and hygiene checks for published paths, real-provider e2e for provider behavior.

Run relevant local checks once before a push. CI owns the exhaustive matrix. `test:coverage`, not `test`, is the coverage gate.

## Conventions

- Put durable rules here only when every task needs them; otherwise link the owning doc.
- Every fact has one home. Link that home instead of restating.
- Non-obvious interfaces get concise JSDoc/doc comments stating behavior, failure modes, timing, and ownership.
- Tests describe behavior, not correctness. Change obsolete behavior with its tests and explain why.
- Files end with exactly one trailing newline.
- Edit this file, not symlinked or generated copies.
