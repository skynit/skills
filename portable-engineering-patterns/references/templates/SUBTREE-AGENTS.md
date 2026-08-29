# AGENTS.md — <SUBTREE>

These local orders supplement the repository root `AGENTS.md`. Do not restate repo-wide rules here.

## What lives in this subtree

- One sentence per owning directory or package.
- State which directories are source, tests, generated output, and fixtures.

## Local authoring rules

- `<RULE>`: one to three lines; link its rationale or owning doc.
- Add a rule only when it is specific to this subtree and not already covered at root.
- Keep a word budget and remove rules that no longer fire.

## Local verification

- The smallest command or focused test that covers a change in this subtree.
- The CI lane that owns exhaustive coverage for this subtree.

## Change record

- Which Agent Note classes or owning docs usually change with this subtree.
- Any generated files that must be regenerated rather than hand-edited.
