#!/usr/bin/env bash
# 把系统 imagegen CLI 接到自建 Sub2API 网关。参数原样透传。
# 详见同目录上一级 SKILL.md。
set -euo pipefail

# 内网网关与其签发的 key（仅内网有效）。环境变量同名可覆盖。
DEFAULT_BASE_URL="http://192.168.100.66:8080/v1"
DEFAULT_API_KEY="sk-890375c09fb9ee17dba2aec38800178d8558f9f9e1a920928ca914006c1da162"

# 默认模型。用 --model 可覆盖，例如 --model gpt-image-2（换回旧模型以解锁自定义尺寸）
DEFAULT_MODEL="gpt-image-2.5-sunburst"

VENV_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/sub2api-imagegen/venv"
IMAGE_GEN="${CODEX_HOME:-$HOME/.codex}/skills/.system/imagegen/scripts/image_gen.py"

if [[ $# -eq 0 ]]; then
  echo "用法: $0 <generate|edit|generate-batch> [参数...]" >&2
  echo "参数与系统 imagegen CLI 相同，见 .system/imagegen/references/cli.md" >&2
  exit 2
fi

if [[ ! -f "$IMAGE_GEN" ]]; then
  echo "找不到 imagegen 脚本: $IMAGE_GEN" >&2
  echo "系统 imagegen skill 可能未安装或被移动。" >&2
  exit 1
fi

export OPENAI_BASE_URL="${OPENAI_BASE_URL:-$DEFAULT_BASE_URL}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-$DEFAULT_API_KEY}"

if [[ -z "$OPENAI_API_KEY" ]]; then
  echo "OPENAI_API_KEY 为空。" >&2
  exit 1
fi

# Clash 等系统代理不要拦截 LAN 网关
gw_host="${OPENAI_BASE_URL#*://}"
gw_host="${gw_host%%/*}"
gw_host="${gw_host%%:*}"
case ",${no_proxy:-}," in
  *",$gw_host,"*) ;;
  *) export no_proxy="${no_proxy:-}${no_proxy:+,}$gw_host" ;;
esac
export NO_PROXY="${NO_PROXY:-$no_proxy}"

has_openai() { "$1" -c 'import openai' >/dev/null 2>&1; }

PY=""
if [[ -n "${IMAGEGEN_PYTHON:-}" ]]; then
  if has_openai "$IMAGEGEN_PYTHON"; then
    PY="$IMAGEGEN_PYTHON"
  else
    echo "IMAGEGEN_PYTHON=$IMAGEGEN_PYTHON 里没有 openai 包。" >&2
    exit 1
  fi
elif command -v python3 >/dev/null 2>&1 && has_openai "$(command -v python3)"; then
  PY="$(command -v python3)"
elif [[ -x "$VENV_DIR/bin/python" ]] && has_openai "$VENV_DIR/bin/python"; then
  PY="$VENV_DIR/bin/python"
else
  echo "未找到带 openai 包的解释器，创建 venv: $VENV_DIR" >&2
  python3 -m venv "$VENV_DIR"
  "$VENV_DIR/bin/pip" install --quiet --upgrade pip openai
  PY="$VENV_DIR/bin/python"
fi

# 未显式指定 --model 时注入默认模型。只对已知子命令注入，避免破坏 -h 等。
TARGET_ARGS=("$@")
case "${1:-}" in
  generate|edit|generate-batch)
    has_model=0
    for arg in "$@"; do
      case "$arg" in --model|--model=*) has_model=1 ;; esac
    done
    if [[ "$has_model" -eq 0 ]]; then
      TARGET_ARGS=("$1" "--model" "$DEFAULT_MODEL" "${@:2}")
    fi
    ;;
esac

exec "$PY" "$IMAGE_GEN" "${TARGET_ARGS[@]}"
