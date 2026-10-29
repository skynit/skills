#!/usr/bin/env bash
set -euo pipefail

# Build deployment artifacts locally. No SSH or production mutations.
if [[ $# -lt 2 || $# -gt 3 ]]; then
  printf 'Usage: bash %s REPO NEW_OUTPUT_DIR [amd64|arm64]\n' "$0" >&2
  exit 2
fi
repo="$(realpath "$1")"
out="$(realpath -m "$2")"
arch="${3:-amd64}"
case "$arch" in amd64|arm64) ;; *) printf 'Unsupported architecture: %s\n' "$arch" >&2; exit 2 ;; esac
for tool in go node npm git sha256sum realpath cp find sort xargs date; do
  command -v "$tool" >/dev/null || { printf 'Missing tool: %s\n' "$tool" >&2; exit 1; }
done
if [[ -e "$out" || -L "$out" ]]; then
  printf 'Output already exists; choose a new release directory: %s\n' "$out" >&2
  exit 1
fi
if [[ "$out" == "$repo" || "$out" == "$repo/"* ]]; then
  printf 'Use an output directory outside the repository.\n' >&2
  exit 1
fi
[[ -f "$repo/src/go.mod" && -f "$repo/vue/package.json" && -f "$repo/vue/nginx.conf" ]] || {
  printf 'Not a bazi repository: %s\n' "$repo" >&2; exit 1;
}
[[ -d "$repo/vue/node_modules" ]] || { printf 'Install frontend dependencies from the lockfile first.\n' >&2; exit 1; }
skill="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
zone="$(go env GOROOT)/lib/time/zoneinfo.zip"
ca="${BAZI_CA_FILE:-/etc/ssl/certs/ca-certificates.crt}"
[[ -f "$zone" && -s "$ca" ]] || { printf 'Missing zoneinfo.zip or CA roots; set BAZI_CA_FILE if needed.\n' >&2; exit 1; }
mkdir -p "$out/backend" "$out/frontend"
trap 'printf "Build incomplete; do not deploy this directory: %s\n" "$out" >&2' ERR
{
  printf 'built_at_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'git_commit=%s\n' "$(git -C "$repo" rev-parse HEAD)"
  printf 'architecture=linux/%s\n' "$arch"
  printf 'go_version=%s\n' "$(go version)"
  printf 'node_version=%s\n' "$(node --version)"
  printf 'workspace_status_begin\n'
  git -C "$repo" status --short --untracked-files=all
  printf 'workspace_status_end\n'
} > "$out/BUILD.txt"
(
  cd "$repo/src"
  CGO_ENABLED=0 GOOS=linux GOARCH="$arch" go build -trimpath -o "$out/backend/server" ./cmd/
)
(
  cd "$repo/vue"
  npm run build -- --outDir "$out/frontend/dist" --emptyOutDir
)
[[ -s "$out/backend/server" && -s "$out/frontend/dist/index.html" ]]
cp "$zone" "$out/backend/zoneinfo.zip"
cp "$ca" "$out/backend/ca-certificates.crt"
cp "$repo/vue/nginx.conf" "$out/frontend/nginx.conf"
cp "$skill/assets/backend.Dockerfile" "$out/backend/Dockerfile"
cp "$skill/assets/frontend.Dockerfile" "$out/frontend/Dockerfile"
cp "$skill/assets/compose.yaml" "$out/docker-compose.yml"
(
  cd "$out"
  find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS
  sha256sum -c SHA256SUMS >/dev/null
)
trap - ERR
printf 'Build ready (not deployed): %s\n' "$out"
