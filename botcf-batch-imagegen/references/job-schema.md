# Generation Job Schema

Use one JSON object per line. Blank lines and lines beginning with `#` are ignored.

## Required fields

| Field | Type | Meaning |
|---|---|---|
| `prompt` | string | Primary image description |
| `size` | string | Final output size such as `1024x1024`, `1536x864`, or `1024x1536` |
| `out` | string | Safe relative output path including extension |

## Optional generation fields

| Field | Default | Meaning |
|---|---|---|
| `model` | `gpt-image-2` | BotCF image model |
| `use_case` | — | Intended product/page use |
| `style` | — | Visual style and medium |
| `composition` | — | Framing, layout, focal placement, negative space |
| `lighting` | — | Lighting and time of day |
| `palette` | — | Dominant and accent colors |
| `constraints` | — | Required exclusions such as no text/logo/watermark |
| `negative` | — | Unwanted styles or artifacts |
| `output_compression` | `82` | Local JPEG/WebP quality, integer 1–100 |
| `key` | output stem | Stable manifest key |
| `metadata` | `{}` | Arbitrary fields copied into the asset manifest |

The script combines the descriptive fields into one structured prompt. The API request contains only `model`, `size`, `n`, and the composed `prompt`.

## Example

```jsonl
{"key":"wood-forest-dawn","prompt":"晨光穿过青绿色山林与薄雾，层叠树木，象征生长与舒展","use_case":"Chinese five-elements blessing page hero","style":"新中式东方自然美学，电影感，写实摄影，安静克制","composition":"wide landscape, title-safe negative space in center-left","lighting":"soft dawn light","palette":"deep forest green, jade green, muted gold","constraints":"无文字，无Logo，无水印，无人物正脸","negative":"卡通，动漫，赛博朋克，过度饱和，模糊，畸变物体","size":"1536x864","output_compression":82,"model":"gpt-image-2","out":"wood/wood-forest-dawn.webp","metadata":{"element":"木","scene":"hero","style":"chinese","focal_x":0.5,"focal_y":0.5}}
{"key":"fire-lantern","prompt":"暮色庭院中的暖红灯笼与轻微薄雾","style":"新中式写实摄影","composition":"vertical editorial composition","lighting":"warm lantern glow","palette":"deep red, amber, muted gold","constraints":"无文字，无Logo，无水印","size":"1024x1536","out":"fire/fire-lantern.webp","metadata":{"element":"火","scene":"general"}}
```

## Naming rules

- Use lowercase ASCII slugs for `key` and filenames.
- Group related files in stable directories such as `wood/`, `hero/`, or `products/`.
- Do not use absolute paths or `..` in `out`.
- Prefer WebP for website assets; use PNG when lossless output is required.
- Keep keys stable even if the prompt changes, unless creating a deliberate version such as `hero-v2`.

## Manifest

The generated manifest has this shape:

```json
{
  "version": 1,
  "assets": [
    {
      "key": "wood-forest-dawn",
      "url": "/generated-assets/wood/wood-forest-dawn.webp",
      "file": "wood/wood-forest-dawn.webp",
      "prompt": "...",
      "width": 1536,
      "height": 864,
      "orientation": "landscape",
      "status": "active",
      "element": "木",
      "scene": "hero"
    }
  ]
}
```

Fields from `metadata` are copied first; generated `key`, `url`, `file`, `prompt`, dimensions, and final status are then normalized.
