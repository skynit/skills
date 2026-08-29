---
name: botcf-batch-imagegen
description: Create and execute resumable BotCF API batch image-generation jobs from JSONL, download URL/base64 responses, convert outputs to requested dimensions and formats, and produce a verified asset manifest. Use when Codex needs to generate many website images, visual material libraries, five-elements assets, hero/gallery/object variants, or reusable image batches through BotCF rather than generating images one at a time.
---

# BotCF Batch Image Generation

Turn a visual asset plan into a repeatable JSONL job file, smoke-test one image, run a resumable batch, and verify every output.

## Workflow

1. Read workspace instructions before creating files.
2. Inspect the target UI and existing asset naming/style when the images belong to a project.
3. Convert the request into a JSONL task file following `references/job-schema.md`.
4. Read the API key from the `BOTCF_API_KEY` environment variable.
5. When the user requests image creation, call the API without asking for confirmation, including for potentially paid smoke tests and full batches.
6. Run `--dry-run` to validate the entire job file.
7. Create a one-line smoke-test job and generate it with concurrency `1`.
8. Verify the smoke image can be decoded and has the expected size. Inspect it visually when image viewing is available.
9. Run the full batch with low concurrency, normally `2`. The script skips existing nonempty outputs, so re-running resumes interrupted work.
10. Verify count, format, dimensions, empty files, duplicate hashes, and manifest paths.
11. Run only the relevant package build/test if assets are being added to a codebase.
12. Report generated paths and validation results.

## Use the Bundled Script

Set the BotCF API key in the environment:

```bash
export BOTCF_API_KEY='<YOUR_BOTCF_API_KEY>'
```

Resolve the global skill directory:

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/botcf-batch-imagegen"
```

Validate without calling the API:

```bash
bash "$SKILL_DIR/scripts/generate-batch.sh" \
  --jobs /absolute/path/generation-jobs.jsonl \
  --out-dir /absolute/path/generated-assets \
  --url-prefix /generated-assets \
  --dry-run
```

Run one smoke-test task:

```bash
bash "$SKILL_DIR/scripts/generate-batch.sh" \
  --jobs /tmp/imagegen-smoke.jsonl \
  --out-dir /tmp/imagegen-smoke \
  --concurrency 1
```

Run the full batch:

```bash
bash "$SKILL_DIR/scripts/generate-batch.sh" \
  --jobs /absolute/path/generation-jobs.jsonl \
  --out-dir /absolute/path/generated-assets \
  --manifest /absolute/path/generated-assets/manifest.json \
  --url-prefix /generated-assets \
  --concurrency 2
```

Use `--force` only when the user explicitly wants existing outputs replaced.

## API Behavior

Use `https://botcf.com/v1` as the default base URL and `POST /images/generations`. The bundled script accepts either `data[0].url` or `data[0].b64_json`, downloads immediately, and converts the result locally with Pillow.

Prefer `gpt-image-2` unless the user or current BotCF documentation requires another model. Do not silently downgrade the model after a failure. Inspect the API response and current documentation first.

Do not pass unsupported OpenAI-specific response options merely to force base64 output. BotCF may return an image URL even when an OpenAI client expects base64; use the bundled direct HTTP script instead.

## Validation

At minimum, validate with Pillow and hashes:

```bash
python3 - <<'PY'
from pathlib import Path
from PIL import Image
import hashlib

root = Path('/absolute/path/generated-assets')
files = sorted(p for p in root.rglob('*') if p.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'})
hashes = {}
for path in files:
    with Image.open(path) as image:
        image.verify()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    hashes.setdefault(digest, []).append(str(path))
print('count:', len(files))
print('duplicates:', [paths for paths in hashes.values() if len(paths) > 1])
PY
```

Treat repeated hashes as suspicious, but distinguish intentional reuse from failed generation before deleting anything.

## Resources

- `scripts/generate-batch.sh`: authenticated, concurrent, retrying, resumable generation runner.
- `references/job-schema.md`: JSONL schema, metadata conventions, and examples.
