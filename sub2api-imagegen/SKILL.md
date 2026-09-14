---
name: sub2api-imagegen
description: Generate or edit raster images through the self-hosted Sub2API gateway using the bundled imagegen CLI (GPT Image models). Use when Codex's built-in image_gen tool is unavailable, or when the user explicitly asks for the Sub2API / CLI image path. Do not use for SVG/vector or code-native visuals.
---

# Sub2API Image Generation

出图的执行层是系统 imagegen skill 的 `scripts/image_gen.py`；本 skill 只负责把它接到自建 Sub2API 网关（`POST /v1/images/generations`，模型 `gpt-image-2`）。

## 何时用

- 内置 `image_gen` 工具不可用（provider 是第三方中转时就是这种情况），但用户需要实际出图。
- 用户明确要求走 Sub2API 或 CLI 路径。

其他情况仍走内置 `image_gen`。

## 前置

- 无需配置凭据：`scripts/generate.sh` 已内置内网网关地址和它签发的 key，开箱即用。
- 同名环境变量 `OPENAI_BASE_URL` / `OPENAI_API_KEY` 可覆盖内置值（换 key、指向别的网关，或临时排障）。
- 该 key 仅在内网有效，且会随公开仓库发布，按公开信息对待。轮换时改脚本里的 `DEFAULT_API_KEY`。

## 用法

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/sub2api-imagegen"
bash "$SKILL_DIR/scripts/generate.sh" generate \
  --prompt "a hero image for a coffee shop landing page" \
  --size 1536x1024 \
  --out output/imagegen/hero.png
```

子命令与参数跟系统 imagegen CLI 完全一致（`generate` / `edit` / `generate-batch`）；完整参数见 `.system/imagegen/references/cli.md`。先用 `--dry-run` 校验 payload，不发请求。

## 脚本行为

`scripts/generate.sh` 做四件事：

1. 用内置的网关地址和 key 设置 `OPENAI_BASE_URL` / `OPENAI_API_KEY`（同名环境变量优先）。
2. 挑一个装了 `openai` 的解释器：`$IMAGEGEN_PYTHON` → 系统 `python3` → `~/.local/share/sub2api-imagegen/venv`（不存在就自动创建并装 `openai`）。
3. 把网关主机加入 `no_proxy`，避免 Clash 之类的系统代理拦截 LAN 请求。
4. 未显式传 `--model` 时注入默认模型 `gpt-image-2.5-sunburst`，其余参数原样转发给 `.system/imagegen/scripts/image_gen.py`。

## 网关注意事项

- 网关提供的图片模型：`gpt-image-2.5-sunburst`（**本技能默认**）、`gpt-image-2.5-flare`、`gpt-image-2`、`gpt-image-1.5`、`gpt-image-1`。**没有裸名 `gpt-image-2.5`**，用 2.5 必须指定变体。不传 `--model` 时包装脚本注入 `gpt-image-2.5-sunburst`；传了就以传入的为准。
- Sunburst 是精度档（细节保真优先），Flare 是速度档，两者同价。要速度、要迭代、或需要自定义尺寸时用 `--model gpt-image-2.5-flare` / `--model gpt-image-2`。
- `--size`：默认模型（2.5）只能用 `1024x1024`、`1536x1024`、`1024x1536`、`auto`；**自定义 `宽x高` 仅 `--model gpt-image-2` 支持**。这是脚本层面的限制，不是网关的。同理 `--quality` 只接受 `low/medium/high/auto`，官方宣传的 `xhigh`/`max` 传不进去。
- 上游可能返回与请求不同的像素尺寸（实测请求 `1024x1024` 返回 `1370x1148`），以文件实际尺寸为准。
- 2.5 系列路由到另一个网关账号（日志里 `account_id: 4`，`gpt-image-2` 是 `account_id: 3`），额度可能独立计算。
- 网关会把请求体的校验失败也映射成 **502**（例如缺 `prompt` 时报 `prompt is required`）。看到 502 先确认参数齐全，别直接判定上游故障。
- 生图消耗网关绑定的 ChatGPT 账号额度，按次计费。
- **不要修改** `.system/imagegen/scripts/image_gen.py`；缺什么先问用户。
