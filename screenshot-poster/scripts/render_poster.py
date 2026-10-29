#!/usr/bin/env python3
"""Compose real screenshots into a PNG and a self-contained SVG."""

import argparse
import base64
import html
import io
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont


def render(spec_path, out_dir, name):
    config = json.loads(spec_path.read_text(encoding="utf-8"))
    width, height = int(config["width"]), int(config["height"])
    scale = int(config.get("scale", 2))
    if min(width, height) <= 0 or not 1 <= scale <= 4:
        raise ValueError("Canvas dimensions must be positive; scale must be 1–4")
    png_path, svg_path = out_dir / f"{name}.png", out_dir / f"{name}.svg"
    if any(p.exists() for p in (png_path, svg_path)):
        raise FileExistsError("Output exists; choose a new --name")
    background = config.get("background", "#171E26")
    family = config.get("font_family", "Noto Sans CJK SC")
    canvas = Image.new("RGBA", (width * scale, height * scale), background)
    draw = ImageDraw.Draw(canvas)
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" '
           f'xmlns:xlink="http://www.w3.org/1999/xlink" width="{width}" '
           f'height="{height}" viewBox="0 0 {width} {height}">',
           f'<rect width="{width}" height="{height}" fill="{html.escape(background, quote=True)}"/>']

    def check_box(x, y, w, h):
        if w <= 0 or h <= 0 or min(x, y) < 0 or x + w > width or y + h > height:
            raise ValueError(f"Layer outside canvas or empty: {(x, y, w, h)}")

    def scaled(box):
        return tuple(round(v * scale) for v in box)

    def get_font(size, weight):
        if weight not in (400, 500, 600, 700):
            raise ValueError("Text weight must be 400, 500, 600, or 700")
        override = config.get("fonts", {}).get(str(weight))
        if override:
            path = Path(override["path"])
            if not path.is_absolute():
                path = spec_path.parent / path
            index = int(override.get("index", 0))
        else:
            style = "Bold" if weight >= 600 else "Medium" if weight == 500 else "Regular"
            path = Path(f"/usr/share/fonts/noto-cjk/NotoSansCJK-{style}.ttc")
            index = 2
            if family != "Noto Sans CJK SC" or not path.exists():
                match = subprocess.run(
                    ["fc-match", "-f", "%{file}\n%{index}", f"{family}:style={style}"],
                    check=True, capture_output=True, text=True,
                ).stdout.splitlines()
                path, index = Path(match[0]), int(match[1]) if len(match) > 1 else 0
        return ImageFont.truetype(str(path), round(size * scale), index=index)

    for number, layer in enumerate(config["layers"]):
        kind = layer["type"]
        x, y = float(layer.get("x", 0)), float(layer.get("y", 0))
        color = layer.get("color", "#EEF3F8")
        escaped_color = html.escape(color, quote=True)
        if kind == "text":
            value, size = str(layer["text"]), float(layer.get("size", 24))
            if not value or size <= 0 or "\n" in value:
                raise ValueError("Use nonempty single-line text with positive size")
            weight = int(layer.get("weight", 400))
            font = get_font(size, weight)
            box = font.getbbox(value, anchor="lt")
            check_box(x + box[0] / scale, y + box[1] / scale,
                      (box[2] - box[0]) / scale, (box[3] - box[1]) / scale)
            draw.text((round(x * scale), round(y * scale)), value,
                      font=font, fill=color, anchor="lt")
            baseline = y - font.getbbox(value, anchor="ls")[1] / scale
            svg.append(f'<text x="{x}" y="{baseline}" '
                       f'font-family="{html.escape(family, quote=True)}, sans-serif" '
                       f'font-size="{size}" font-weight="{weight}" '
                       f'fill="{escaped_color}">{html.escape(value)}</text>')
        elif kind == "rect":
            w, h = float(layer["width"]), float(layer["height"])
            radius = float(layer.get("radius", 0))
            check_box(x, y, w, h)
            draw.rounded_rectangle(scaled((x, y, x + w, y + h)),
                                   radius=round(radius * scale), fill=color)
            svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
                       f'rx="{radius}" fill="{escaped_color}"/>')
        elif kind == "line":
            x1, y1, x2, y2 = (float(layer[key]) for key in ("x1", "y1", "x2", "y2"))
            if min(x1, x2) < 0 or min(y1, y2) < 0 or max(x1, x2) > width or max(y1, y2) > height:
                raise ValueError("Line outside canvas")
            thickness = float(layer.get("width", 1))
            if thickness <= 0:
                raise ValueError("Line width must be positive")
            draw.line(scaled((x1, y1, x2, y2)), fill=color,
                      width=max(1, round(thickness * scale)))
            svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                       f'stroke="{escaped_color}" stroke-width="{thickness}"/>')
        elif kind == "image":
            path = Path(layer["path"])
            if not path.is_absolute():
                path = spec_path.parent / path
            with Image.open(path) as source:
                image = source.convert("RGBA")
            if "crop" in layer:
                left, top, right, bottom = map(int, layer["crop"])
                if not (0 <= left < right <= image.width and 0 <= top < bottom <= image.height):
                    raise ValueError(f"Invalid crop for {path}")
                image = image.crop((left, top, right, bottom))
            w = round(float(layer["width"]))
            h = max(1, round(image.height * w / image.width))
            check_box(x, y, w, h)
            radius = float(layer.get("radius", 0))
            resized = image.resize((w * scale, h * scale), Image.Resampling.LANCZOS)
            mask = Image.new("L", resized.size)
            ImageDraw.Draw(mask).rounded_rectangle(
                (0, 0, resized.width - 1, resized.height - 1),
                radius=round(radius * scale), fill=255)
            resized.putalpha(ImageChops.multiply(resized.getchannel("A"), mask))
            if "shadow" in layer:
                shadow = layer["shadow"]
                dx, dy = float(shadow.get("x", 0)), float(shadow.get("y", 18))
                blur = float(shadow.get("blur", 22))
                opacity = float(shadow.get("opacity", 0.33))
                if blur < 0 or not 0 <= opacity <= 1:
                    raise ValueError("Shadow blur must be nonnegative; opacity must be 0–1")
                shadow_canvas = Image.new("RGBA", canvas.size)
                shadow_alpha = resized.getchannel("A").point(lambda value: round(value * opacity))
                shadow_image = Image.new("RGBA", resized.size)
                shadow_image.putalpha(shadow_alpha)
                shadow_canvas.alpha_composite(shadow_image, scaled((x + dx, y + dy)))
                canvas.alpha_composite(shadow_canvas.filter(ImageFilter.GaussianBlur(blur * scale)))
                svg.append(f'<defs><filter id="s{number}" x="-100%" y="-100%" width="300%" height="300%">'
                           f'<feDropShadow dx="{dx}" dy="{dy}" stdDeviation="{blur}" '
                           f'flood-color="#000000" flood-opacity="{opacity}"/></filter></defs>')
            canvas.alpha_composite(resized, scaled((x, y)))
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            data = base64.b64encode(buffer.getvalue()).decode("ascii")
            svg.append(f'<defs><clipPath id="c{number}"><rect x="{x}" y="{y}" '
                       f'width="{w}" height="{h}" rx="{radius}"/></clipPath></defs>')
            svg.append(f'<g'+(f' filter="url(#s{number})"' if "shadow" in layer else '')+'>'
                       f'<image x="{x}" y="{y}" width="{w}" height="{h}" '
                       f'clip-path="url(#c{number})" xlink:href="data:image/png;base64,{data}"/></g>')
        else:
            raise ValueError(f"Unknown layer type: {kind}")
    svg.append("</svg>")
    out_dir.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").resize((width, height), Image.Resampling.LANCZOS).save(png_path, optimize=True)
    svg_path.write_text("\n".join(svg), encoding="utf-8")
    print(png_path)
    print(svg_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--name", default="poster")
    args = parser.parse_args()
    if not args.name or args.name in (".", "..") or Path(args.name).name != args.name:
        parser.error("--name must be a filename stem without directories")
    render(args.spec.resolve(), args.out_dir.resolve(), args.name)


if __name__ == "__main__":
    main()
