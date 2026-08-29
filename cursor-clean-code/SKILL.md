---
name: cursor-clean-code
description: Keep code changes clean, readable, and deliberately small. Use when writing, reviewing, or refactoring code where scope control, maintainability, meaningful naming, restrained abstraction, and avoidance of over-engineering matter.
license: CC0-1.0
---

# Cursor Clean Code

Apply clean-code practices without turning a focused change into a redesign. Optimize for correct, understandable code and the smallest coherent change, not the fewest lines.

## Working Rules

1. Understand the existing behavior, callers, tests, and project instructions before editing.
2. Change only what the request requires. Do not rewrite adjacent code merely because it could look different.
3. Preserve observable behavior during refactoring: inputs, outputs, side effects, errors, ordering, and edge cases.
4. Follow the repository's existing naming, structure, typing, error-handling, and testing conventions.
5. Prefer the simplest implementation that fully satisfies the request. Add an abstraction only when it removes demonstrated duplication or isolates a real responsibility.
6. Use meaningful names. Avoid abbreviations unless they are established domain terms.
7. Replace unexplained magic values with named constants when doing so improves meaning. Do not create a constants layer for one obvious local value.
8. Keep functions focused, but do not split code into trivial wrappers that make control flow harder to follow.
9. Reduce deep nesting with guard clauses or well-named helpers when behavior stays clear.
10. Comment why a non-obvious constraint exists. Do not narrate self-explanatory statements.
11. Keep related code together and preserve encapsulation. Expose the smallest useful interface.
12. Deduplicate only when the repeated logic is genuinely the same concept and is likely to evolve together.

## Restraint Gate

Do not:

- modify unrelated files or public APIs;
- introduce dependencies, frameworks, patterns, or configuration without a concrete need;
- add speculative extensibility, generic factories, builders, registries, or layers for a single use case;
- add defensive handling for states ruled out by an established contract;
- replace readable code with dense expressions, clever chaining, or nested ternaries;
- combine a behavior change and a broad cleanup unless the user explicitly requests both;
- treat line count as the primary quality metric.

If a broader cleanup would be valuable but is outside scope, report it separately instead of implementing it.

## Verification

Before delivery:

1. Inspect the diff and confirm every changed file is necessary for the request.
2. Check that the result is simpler to understand, not merely shorter or more abstract.
3. Run the narrowest relevant tests or checks allowed by the repository instructions.
4. Confirm behavior-preservation claims against tests or concrete evidence; state any unverified assumptions.

## Upstream

This Codex adaptation is derived from `clean-code.mdc` and `anti-overengineering.mdc` in `PatrickJS/awesome-cursorrules` at commit `b044f956f021b6e8877f16781bcfc466a6a120e9`. See [references/upstream.md](references/upstream.md).
