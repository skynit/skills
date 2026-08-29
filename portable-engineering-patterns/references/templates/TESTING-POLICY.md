# Testing policy

One home for how this project tests and how a contributor chooses evidence. Commands live in the root `AGENTS.md`; this file owns tier semantics and policy.

## Tiers

| Tier | Command | What it proves | When it runs |
|---|---|---|---|
| Unit and integration | `<test>` | Behavior, error paths, ordering, races, disposal | Locally, focused |
| Coverage gate | `<test:coverage>` | Required source is executed, dead code is found | CI |
| Keyless snapshot | `<test:snapshot>` | Stable model, API, CLI, or UI output; persisted logs replay | Locally and CI |
| Real-provider e2e | `<test:e2e>` | Live provider and assembled product work | CI with secret; self-skips without |
| Build and hygiene | `<build>`, `<hygiene>` | Shipped artifacts, exports, constraints, published paths | CI and selected local checks |

Coverage is necessary, never sufficient. Prefer the real implementation and mock only the expensive or nondeterministic boundary.

## Evidence selection

- Package or module behavior: the owning focused test, plus adjacent tests when a shared contract changes.
- Model-visible, CLI-visible, or API-visible output: the owning snapshot or real runnable example.
- Documentation, records, and generated catalogs: the documentation gate.
- Public exports, packaging, build config, or binaries: build, hygiene, and the owning built-artifact smoke.
- Provider behavior: the relevant with-key e2e smoke.

Do not run the full suite merely because a commit or push follows. CI owns the exhaustive matrix and platform coverage.

## With-key policy

A no-key test proves plumbing; a with-key run proves the product against a real provider. Cover file-writing prompts, multi-turn conversations, tool use, and cancellation. Suites self-skip without a secret. A trusted CI lane that must carry the secret fails its preflight when the secret is absent; never let skips look like coverage.

## Snapshot policy

Snapshots pin expected outputs and are keyless. Record or refresh only locally. Review every expected-output diff as a behavior change. CI replays read-only and never writes golden files.

## Assertion rules

- Assert external state or persisted logs, never an agent's self-report.
- Verify untouched files byte-for-byte.
- Boot through the real entry path; a hand-mounted fixture can miss loader or configuration failures.
- Test denial through the executor that enforces it, not the prompt or schema alone.
- Tests own their resources and dispose them even on failure or timeout.
