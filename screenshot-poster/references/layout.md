# 排版配置与双截图示例

## 本次案例

素材为同一 AI 桌面部件的收起总览和展开详情。第一张原图 `970×498`，裁切框为 `[0,0,970,418]`，去掉底部桌面工具条；第二张 `968×1266`，保留完整内容。保留焦点框与鼠标，没有重绘截图。

| 对象 | 参数 |
| --- | --- |
| 画布 | 1920×1080 |
| 背景 / 主字 / 辅字 | #171E26 / #EEF3F8 / #9AA8B5 |
| 强调 / 高亮 | #4D8DFF / #A9C7FF |
| 主标题 | x=108，y=231，78px，600 字重 |
| 总览图 | x=112，y=464，width=800，高度按比例计算 |
| 详情图 | x=1144，y=120，width=664，高度按比例计算 |
| 图片圆角 | 14px，用于宣传合成而非修改应用 |
| 投影 | x=0，y=18，模糊半径=22，黑色透明度约 33% |
| 底部功能说明 | 三组：工具总览 / 每日趋势 / 模型费用 |

这些参数是案例参考，不是其他素材必须遵守的模板。竖图放不下时调整比例或另做详情图，不拉伸图片。

## JSON 格式

`width`、`height` 是画布像素尺寸。`scale` 为 PNG 内部渲染倍率，默认 2，最终仍输出指定画布尺寸；SVG 始终保存原始坐标。

`layers` 按绘制顺序列出对象：

- `text`：`x,y,text,size,color,weight`。`y` 是字形可见顶部；支持 400/500/600/700 字重。中英文、标点以实际渲染检查为准。
- `image`：`x,y,path,width`；高度自动保持比例。可选 `crop:[left,top,right,bottom]`，坐标基于原图；`radius` 控制外角，`shadow` 配置投影。透明截图保留原 alpha。
- `line`：`x1,y1,x2,y2,color,width`。
- `rect`：`x,y,width,height,color,radius`。

图片相对路径以 JSON 所在目录解析。所有图层需完整落在画布内；脚本会检查边界，不检查图层之间是否重叠，因为图片、文字覆盖有时是设计意图。

下面是最小配置。先把 `overview.png` 和 `detail.png` 换成实际素材路径，标题与项目名称按当前项目填写，不擅自沿用案例身份。

```json
{
  "width": 1920,
  "height": 1080,
  "background": "#171E26",
  "font_family": "Noto Sans CJK SC",
  "layers": [
    {"type":"text", "x":112, "y":96, "text":"项目名称", "size":28, "weight":500},
    {"type":"text", "x":112, "y":231, "text":"AI 用量，一处查看。", "size":72, "weight":600, "color":"#A9C7FF"},
    {"type":"text", "x":112, "y":341, "text":"从工具总览，到每日用量与模型费用。", "size":26, "color":"#9AA8B5"},
    {"type":"image", "x":112, "y":464, "path":"overview.png", "crop":[0,0,970,418], "width":800, "radius":14, "shadow":{"x":0,"y":18,"blur":22,"opacity":0.33}},
    {"type":"image", "x":1144, "y":120, "path":"detail.png", "width":664, "radius":14, "shadow":{"x":0,"y":18,"blur":22,"opacity":0.33}},
    {"type":"line", "x1":112, "y1":1000, "x2":1808, "y2":1000, "color":"#2B3947", "width":1}
  ]
}
```

## 字体与格式边界

本机脚本优先使用 `/usr/share/fonts/noto-cjk/NotoSansCJK-*.ttc` 的简体中文字库（index=2）；缺失时通过 `fc-match` 查找配置中的字体族。换机器后先检查字体，不默认下载字体。

可在顶层 `fonts` 中覆盖字重的字体文件：

```json
{"fonts":{"400":{"path":"/absolute/path/font.ttc","index":2}}}
```

SVG 嵌入裁切后的截图，文字作为独立 `<text>` 对象保留。Pillow 的模糊半径与 SVG 的高斯模糊参数并非跨软件像素级一致；PNG 是经过目视检查的预览，SVG 导入 Figma 后检查阴影和字体再交付。不能把 SVG 称为已验证的原生 Figma 文件。
