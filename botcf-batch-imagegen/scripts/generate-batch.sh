#!/usr/bin/env bash
set -euo pipefail

JOBS_FILE="${JOBS_FILE:-}"
OUT_DIR="${OUT_DIR:-}"
MANIFEST_FILE="${MANIFEST_FILE:-}"
URL_PREFIX="${URL_PREFIX:-/generated-assets}"
BOTCF_BASE_URL="${BOTCF_BASE_URL:-https://botcf.com/v1}"
CONCURRENCY="${CONCURRENCY:-2}"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-3}"
FORCE="${FORCE:-0}"
DRY_RUN=0
WRITE_MANIFEST=1

usage() {
  cat <<'EOF'
Usage:
  generate-batch.sh --jobs FILE --out-dir DIR [options]

Required:
  --jobs FILE             JSONL task file
  --out-dir DIR           Output directory

Options:
  --manifest FILE         Manifest path (default: OUT_DIR/manifest.json)
  --url-prefix PREFIX     URL prefix written to manifest (default: /generated-assets)
  --base-url URL          BotCF OpenAI-compatible base URL
  --concurrency N         Parallel requests (default: 2)
  --max-attempts N        Attempts per image (default: 3)
  --force                 Replace existing outputs
  --dry-run               Validate and print plan without using the API
  --no-manifest           Do not write manifest.json
  -h, --help              Show this help

Authentication:
  Export BOTCF_API_KEY. OPENAI_API_KEY is accepted as a fallback.
  Optionally store BOTCF_API_KEY in ~/.config/botcf/imagegen.env (chmod 600).
EOF
}

while (($#)); do
  case "$1" in
    --jobs) JOBS_FILE="${2:?missing value for --jobs}"; shift 2 ;;
    --out-dir) OUT_DIR="${2:?missing value for --out-dir}"; shift 2 ;;
    --manifest) MANIFEST_FILE="${2:?missing value for --manifest}"; shift 2 ;;
    --url-prefix) URL_PREFIX="${2:?missing value for --url-prefix}"; shift 2 ;;
    --base-url) BOTCF_BASE_URL="${2:?missing value for --base-url}"; shift 2 ;;
    --concurrency) CONCURRENCY="${2:?missing value for --concurrency}"; shift 2 ;;
    --max-attempts) MAX_ATTEMPTS="${2:?missing value for --max-attempts}"; shift 2 ;;
    --force) FORCE=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --no-manifest) WRITE_MANIFEST=0; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "$JOBS_FILE" || -z "$OUT_DIR" ]]; then
  usage >&2
  exit 2
fi
if [[ -z "$MANIFEST_FILE" ]]; then
  MANIFEST_FILE="$OUT_DIR/manifest.json"
fi
if [[ ! -f "$JOBS_FILE" ]]; then
  echo "Job file not found: $JOBS_FILE" >&2
  exit 1
fi
if ! [[ "$CONCURRENCY" =~ ^[1-9][0-9]*$ && "$MAX_ATTEMPTS" =~ ^[1-9][0-9]*$ ]]; then
  echo "--concurrency and --max-attempts must be positive integers" >&2
  exit 2
fi
for command in curl jq python3; do
  command -v "$command" >/dev/null || { echo "Missing command: $command" >&2; exit 1; }
done
python3 - <<'PY' >/dev/null
from PIL import Image
PY

python3 - "$JOBS_FILE" <<'PY'
import json, sys
from pathlib import PurePosixPath
count = 0
for line_no, raw in enumerate(open(sys.argv[1], encoding="utf-8"), 1):
    raw = raw.strip()
    if not raw or raw.startswith("#"):
        continue
    count += 1
    try:
        job = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON at line {line_no}: {exc}")
    for field in ("prompt", "out", "size"):
        if not job.get(field):
            raise SystemExit(f"Missing {field!r} at line {line_no}")
    path = PurePosixPath(job["out"])
    if path.is_absolute() or ".." in path.parts or not path.suffix:
        raise SystemExit(f"Unsafe or extensionless output path at line {line_no}: {path}")
    try:
        width, height = map(int, str(job["size"]).lower().split("x", 1))
        if width < 64 or height < 64:
            raise ValueError
    except ValueError:
        raise SystemExit(f"Invalid size at line {line_no}: {job['size']}")
if not count:
    raise SystemExit("No jobs found")
print(f"Validated {count} generation jobs")
PY

mapfile -t JOBS < <(grep -vE '^[[:space:]]*(#|$)' "$JOBS_FILE")
TOTAL="${#JOBS[@]}"

if ((DRY_RUN)); then
  for i in "${!JOBS[@]}"; do
    jq -r --arg index "$((i + 1))" '"[" + $index + "] " + (.model // "gpt-image-2") + " " + .size + " -> " + .out' <<<"${JOBS[$i]}"
  done
  exit 0
fi

ENV_FILE="${BOTCF_ENV_FILE:-$HOME/.config/botcf/imagegen.env}"
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi
API_KEY="${BOTCF_API_KEY:-${OPENAI_API_KEY:-}}"
if [[ -z "$API_KEY" ]]; then
  echo "Set BOTCF_API_KEY or create $ENV_FILE" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/botcf-batch-imagegen.XXXXXX")"
trap 'rm -rf "$WORK_DIR"' EXIT
mkdir -p "$WORK_DIR/failures"

build_payload() {
  local job_file="$1" payload_file="$2"
  python3 - "$job_file" "$payload_file" <<'PY'
import json, sys
job = json.load(open(sys.argv[1], encoding="utf-8"))
labels = {
    "prompt": "Subject", "use_case": "Use case", "style": "Style",
    "composition": "Composition", "lighting": "Lighting", "palette": "Palette",
    "constraints": "Requirements", "negative": "Avoid",
}
parts = [f"{labels[key]}: {job[key]}" for key in labels if job.get(key)]
payload = {
    "model": job.get("model", "gpt-image-2"),
    "size": job.get("size", "1024x1024"),
    "n": 1,
    "prompt": "\n".join(parts),
}
json.dump(payload, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False)
PY
}

save_image() {
  local source_file="$1" output_file="$2" size="$3" compression="$4"
  python3 - "$source_file" "$output_file" "$size" "$compression" <<'PY'
import sys
from pathlib import Path
from PIL import Image, ImageOps
source, output, size, compression = sys.argv[1:]
width, height = map(int, size.lower().split("x", 1))
out = Path(output)
out.parent.mkdir(parents=True, exist_ok=True)
with Image.open(source) as image:
    image = ImageOps.exif_transpose(image).convert("RGB")
    if image.size != (width, height):
        image = ImageOps.fit(image, (width, height), method=Image.Resampling.LANCZOS)
    temp = out.with_name(out.name + ".part")
    fmt = out.suffix.lstrip(".").upper()
    if fmt == "JPG":
        fmt = "JPEG"
    options = {"quality": int(compression), "optimize": True}
    if fmt == "WEBP":
        options["method"] = 6
    image.save(temp, format=fmt, **options)
    temp.replace(out)
PY
}

generate_one() {
  local index="$1" job_json="$2" job_dir="$WORK_DIR/job-$1"
  mkdir -p "$job_dir"
  printf '%s\n' "$job_json" > "$job_dir/job.json"

  local relative_out size compression output_file attempt image_url image_b64
  relative_out="$(jq -er '.out' "$job_dir/job.json")"
  size="$(jq -er '.size' "$job_dir/job.json")"
  compression="$(jq -er '.output_compression // 82' "$job_dir/job.json")"
  output_file="$OUT_DIR/$relative_out"

  if [[ -s "$output_file" && "$FORCE" != "1" ]]; then
    echo "[job $index/$TOTAL] exists, skipping: $relative_out"
    return 0
  fi

  build_payload "$job_dir/job.json" "$job_dir/payload.json"
  for ((attempt = 1; attempt <= MAX_ATTEMPTS; attempt++)); do
    echo "[job $index/$TOTAL] generating ($attempt/$MAX_ATTEMPTS): $relative_out"
    if curl --fail-with-body --silent --show-error --location \
      --connect-timeout 20 --max-time 360 \
      "$BOTCF_BASE_URL/images/generations" \
      -H "Authorization: Bearer $API_KEY" \
      -H 'Content-Type: application/json' \
      --data-binary "@$job_dir/payload.json" \
      -o "$job_dir/response.json"; then
      image_url="$(jq -r '.data[0].url // empty' "$job_dir/response.json" 2>/dev/null || true)"
      image_b64="$(jq -r '.data[0].b64_json // empty' "$job_dir/response.json" 2>/dev/null || true)"
      if [[ -n "$image_url" ]]; then
        curl --fail --silent --show-error --location --connect-timeout 20 --max-time 180 --retry 2 \
          "$image_url" -o "$job_dir/source-image" || true
      elif [[ -n "$image_b64" ]]; then
        printf '%s' "$image_b64" | base64 --decode > "$job_dir/source-image" || true
      fi
      if [[ -s "$job_dir/source-image" ]] && save_image "$job_dir/source-image" "$output_file" "$size" "$compression"; then
        echo "[job $index/$TOTAL] complete: $relative_out"
        return 0
      fi
    fi
    ((attempt < MAX_ATTEMPTS)) && sleep $((attempt * 3))
  done

  echo "[job $index/$TOTAL] failed: $relative_out" >&2
  touch "$WORK_DIR/failures/$index"
  return 1
}

pids=()
for i in "${!JOBS[@]}"; do
  generate_one "$((i + 1))" "${JOBS[$i]}" &
  pids+=("$!")
  if ((${#pids[@]} >= CONCURRENCY)); then
    wait "${pids[0]}" || true
    pids=("${pids[@]:1}")
  fi
done
for pid in "${pids[@]}"; do
  wait "$pid" || true
done

FAILURES="$(find "$WORK_DIR/failures" -type f | wc -l)"
if ((FAILURES > 0)); then
  echo "Batch incomplete: $FAILURES/$TOTAL jobs failed. Re-run to resume." >&2
  exit 1
fi

if ((WRITE_MANIFEST)); then
  python3 - "$JOBS_FILE" "$OUT_DIR" "$MANIFEST_FILE" "$URL_PREFIX" <<'PY'
import json, sys
from pathlib import Path
from PIL import Image
jobs_file, out_dir, manifest_file = map(Path, sys.argv[1:4])
url_prefix = sys.argv[4].rstrip("/")
assets = []
for index, raw in enumerate(jobs_file.read_text(encoding="utf-8").splitlines(), 1):
    raw = raw.strip()
    if not raw or raw.startswith("#"):
        continue
    job = json.loads(raw)
    rel = Path(job["out"])
    with Image.open(out_dir / rel) as image:
        width, height = image.size
    ratio = width / height
    orientation = "square" if 0.9 <= ratio <= 1.1 else ("landscape" if ratio > 1 else "portrait")
    asset = dict(job.get("metadata") or {})
    asset.update({
        "key": job.get("key", rel.stem),
        "url": f"{url_prefix}/{rel.as_posix()}" if url_prefix else rel.as_posix(),
        "file": rel.as_posix(),
        "prompt": job["prompt"],
        "width": width,
        "height": height,
        "orientation": asset.get("orientation", orientation),
        "status": asset.get("status", "active"),
    })
    assets.append(asset)
manifest_file.parent.mkdir(parents=True, exist_ok=True)
manifest_file.write_text(json.dumps({"version": 1, "assets": assets}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Wrote manifest: {manifest_file} ({len(assets)} assets)")
PY
fi

echo "Batch complete: $TOTAL images"
