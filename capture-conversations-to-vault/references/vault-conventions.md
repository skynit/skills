# Vault Conventions

## Contents

1. Vault identity
2. Authority files
3. Classification
4. Conversation handling
5. Destination and merge rules
6. Frontmatter and structure
7. Naming and links
8. Operational-note rules
9. Source quality and privacy
10. Validation checklist

## 1. Vault Identity

- Root: `/home/skynit/workspace/note`
- Format: Obsidian Markdown
- Language: Chinese by default
- Organization: numbered top-level domains

## 2. Authority Files

Read these before changing classification behavior:

- `00-知识库/01-规范/知识库分类规范.md`
- `00-知识库/首页.md`
- the destination domain's `00-索引.md` or MOC
- the closest file under `00-知识库/02-模板/`

Historical-summary examples:

- `30-系统工程/02-Linux内核与驱动/90-历史会话汇总/硬件与驱动.md`
- `30-系统工程/04-网络与无线/90-历史会话汇总/网络与无线技术.md`

## 3. Classification

Apply the vault's single-physical-home rule. Express cross-domain relationships with links and tags.

| Destination | Content |
| --- | --- |
| `01-收件箱` | Ownership cannot yet be determined |
| `10-计算机科学` | Stable theory, academic material, foundational models |
| `20-软件开发` | Languages, frameworks, databases, testing, Git, developer tools |
| `30-系统工程` | Linux operations, kernel, drivers, networking, storage, containers, desktop |
| `40-AI与自动化` | LLM tools, AI workflows, automation |
| `50-命理` | 命理原文、概念、技法和专题研究 |
| `70-项目` | Material owned by a concrete product or deliverable |
| `80-日记` | Date-based journal entries |
| `90-原始资料` | Unprocessed transcripts, clippings, external repositories |
| `99-归档` | Superseded or inactive material retained for traceability |

Do not use `99-归档` for unclassified content.

## 4. Conversation Handling

Distinguish three artifacts:

1. **Raw transcript**: Create only when explicitly requested. Treat as source material, not a durable note.
2. **Historical summary**: Put under the relevant domain's `90-历史会话汇总/`. Keep it separate from atomic notes.
3. **Durable synthesis**: Merge reusable knowledge into the domain or project note that owns the topic.

Default to durable synthesis when the user says “插入知识库”“整理到知识库” or asks to update a named note. Do not create both a transcript and synthesis unless requested.

Related side threads are evidence sources, not automatic destinations. Include only material that changes or strengthens the resulting note.

## 5. Destination and Merge Rules

Search before creating:

```bash
rg -n -i '<topic-or-identifier>' /home/skynit/workspace/note -g '*.md'
```

Prefer, in order:

1. User-specified target note.
2. Existing durable note with the same subject.
3. Existing project note when the knowledge is deliverable-specific.
4. Existing domain history summary for explicit archival requests.
5. A new descriptive note in the correct domain.
6. `01-收件箱` when ownership remains ambiguous.

Never duplicate an existing procedure into a second physical note solely because a side thread used a different title.

When a new durable note has an obvious MOC, add one concise full-path wiki link. Do not reorganize the MOC.

## 6. Frontmatter and Structure

Preserve existing frontmatter exactly except fields that genuinely need updates.

For a new curated note, prefer the closest template. A common shape is:

```yaml
---
title: 主题名称
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: concept-or-command
tags:
  - 标签
---
```

Historical summaries commonly use:

```yaml
---
date: YYYY-MM-DD
tags: [codex, topic, summary]
category: domain
---
```

Do not normalize an existing note from one schema to the other without a separate migration request.

Every note needs one H1 matching the subject. Avoid duplicate H1 headings.

## 7. Naming and Links

- Use descriptive Chinese filenames; avoid `note1`, `其他`, and generic chat titles.
- Keep top-level two-digit prefixes unchanged.
- Use `[[完整/知识库/路径|显示名称]]` in MOCs.
- Use `[[唯一概念]]` only when the target is unambiguous inside the domain.
- Check Markdown relative links and local images after moving or creating a note.
- Do not use absolute filesystem Markdown links inside the vault as a substitute for wiki links.

## 8. Operational-Note Rules

For Linux, driver, networking, installation, deployment, or troubleshooting notes:

1. Put the user-approved runnable workflow first.
2. Keep the source command order and exact flags.
3. Put verification next.
4. Put explanation, known-good output, failures, and background afterward.
5. Use one command per code block when terminal paste behavior requires it.
6. Separate observed results from proposed next steps.
7. Do not insert extra dependencies, cleanup, optimization, rollback, or boot commands into the primary workflow without source authority.

If a repository path in the canonical note is demonstrably stale, correct only that path and state the observed evidence.

## 9. Source Quality and Privacy

Use this precedence:

1. Latest explicit user correction.
2. User-designated canonical note.
3. Directly inspected logs/files/tool output.
4. Official documentation.
5. Older conversation claims.
6. Assistant summaries.

Remove rejected approaches when the user says they are wrong or out of scope. Do not retain them as a “complete history” unless archival history was requested.

Never store literal credentials. Redact:

- passwords and tokens;
- private keys and cookies;
- `sshpass`/`SSHPASS` values;
- authorization headers;
- unnecessary personal identifiers.

Use placeholders. Keep hardware IDs, hashes, versions, and error codes when they are material to reproducibility.

## 10. Validation Checklist

- Correct single physical destination.
- Existing note reused when appropriate.
- Current user correction applied.
- Side-thread claims reconciled, not concatenated.
- Primary procedure appears first for operational notes.
- No unauthorized procedure expansion.
- Frontmatter follows the selected local pattern.
- One H1.
- Paired code fences.
- Obsidian wiki links used correctly.
- No credentials or TODO placeholders.
- New note linked from an obvious MOC only when appropriate.
