#!/usr/bin/env python3
"""Validate a Markdown note against the local Obsidian vault's core rules."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


DEFAULT_VAULT = Path("/home/skynit/workspace/note")
WIKI_LINK_RE = re.compile(r"\[\[(?!:)([^\[\]|#]+)(?:#[^\[\]|]+)?(?:\|[^\]]+)?\]\]")
SECRET_PATTERNS = {
    "SSHPASS assignment": re.compile(r"\bSSHPASS\s*=\s*[^<\s]+", re.IGNORECASE),
    "sshpass literal password": re.compile(r"\bsshpass\s+-p\s+['\"]?(?!<)[^\s'\"]+", re.IGNORECASE),
    "authorization header": re.compile(r"\bAuthorization\s*:\s*(?:Bearer|Basic)\s+(?!<)[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    "explicit password statement": re.compile(r"(?:密码(?:是|为)|password\s+is)\s*[:：=]?\s*(?!<|CHANGE_ME)[^\s`]+", re.IGNORECASE),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notes", nargs="+", type=Path, help="Markdown note paths")
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT, help="Vault root")
    return parser.parse_args()


def within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def resolve_wiki_target(target: str, note: Path, vault: Path) -> bool:
    normalized = target.strip().removesuffix(".md")
    if not normalized:
        return True

    direct = vault / (normalized + ".md")
    if direct.exists():
        return True

    relative = note.parent / (normalized + ".md")
    if relative.exists():
        return True

    if "/" not in normalized:
        return any(vault.rglob(normalized + ".md"))

    return False


def validate(note: Path, vault: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    note = note.expanduser().resolve()
    vault = vault.expanduser().resolve()

    if not within(note, vault):
        return [f"note is outside vault: {note}"], warnings
    if note.suffix.lower() != ".md":
        errors.append("note must use the .md extension")
    if not note.is_file():
        return [f"note does not exist: {note}"], warnings

    text = note.read_text(encoding="utf-8")
    lines = text.splitlines()

    if not lines or lines[0].strip() != "---":
        errors.append("missing YAML frontmatter at file start")
        frontmatter_end = -1
    else:
        frontmatter_end = next((i for i, line in enumerate(lines[1:], 1) if line.strip() == "---"), -1)
        if frontmatter_end < 0:
            errors.append("unclosed YAML frontmatter")
        else:
            frontmatter = "\n".join(lines[1:frontmatter_end])
            if not re.search(r"^(?:title|date):\s*\S", frontmatter, re.MULTILINE):
                errors.append("frontmatter needs a non-empty title or date")

    prose_lines: list[str] = []
    in_fence = False
    for line in lines:
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            prose_lines.append(line)
    prose_text = "\n".join(prose_lines)

    h1_lines = [line for line in prose_lines[frontmatter_end + 1 :] if re.match(r"^#\s+\S", line)]
    if not h1_lines:
        errors.append("missing H1 heading")
    elif len(h1_lines) > 1:
        warnings.append(f"multiple H1 headings: {len(h1_lines)}")

    fence_count = sum(1 for line in lines if line.startswith("```"))
    if fence_count % 2:
        errors.append(f"unpaired fenced code block markers: {fence_count}")

    if re.search(r"\b(?:TODO|TBD)\b|\{\{[^}]+\}\}", prose_text):
        errors.append("unresolved TODO/TBD/template placeholder")

    for label, pattern in SECRET_PATTERNS.items():
        if pattern.search(text):
            errors.append(f"possible secret: {label}")

    missing_links = sorted(
        target for target in set(WIKI_LINK_RE.findall(prose_text)) if not resolve_wiki_target(target, note, vault)
    )
    for target in missing_links:
        warnings.append(f"unresolved wiki link: [[{target}]]")

    return errors, warnings


def main() -> int:
    args = parse_args()
    vault = args.vault.expanduser().resolve()
    failed = False

    for note in args.notes:
        errors, warnings = validate(note, vault)
        print(f"{note}:")
        for warning in warnings:
            print(f"  WARNING: {warning}")
        for error in errors:
            print(f"  ERROR: {error}")
        if not warnings and not errors:
            print("  OK")
        failed = failed or bool(errors)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
