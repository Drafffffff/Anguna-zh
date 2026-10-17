# Anguna 图形汉化

`ANGUNA/tools/graphics_zh.py` 提供 `apply_graphics(bytearray, preview=True) -> dict`，调用者负责最终 ROM 输出。仅替换标题与 Game Over 两组固定容量的 8bpp tile/map 数据，不修改调色板、资源加载长度、指针、地图尺寸或代码。

- 标题保留 ANGUNA 商标与背景角色。嵌在景物中的 Warriors of Virtue 用深绿金边像素牌替换为「美德勇士」。
- 结束画面 GAME OVER 替换为棕色金边「游戏结束」像素牌。
- 两处 NEW GAME / CONTINUE 分别替换为「新游戏 / 继续游戏」，字体为 Fusion Pixel 原生 12px 点阵。
- 大字采用原生 12px 点阵整数放大 2 倍；不使用矢量抗锯齿、插值或 AI 绘图。
- 两处选项保留原始颜色索引；标题为 254/255，结束画面为 16/33，故原有选项变色逻辑仍可工作。
- 原 map 箭头覆盖区 x14..16、y16..17 和备用箭头 y20..21 的像素严格保留。tile 编号经重新去重变化，但 map 指向相应新编号；地图各元素位置不变。
- tiles 做精确像素与水平/垂直翻转去重，原资源空间足够：标题 435/456 个，结束 404/437 个。剩余容量补零，原加载长度不变。
- 编码后再次解码，验证整个 256×176 目标图逐索引字节一致；原调色板完全不变。
- HUD 的 320 个 4bpp tile 已解码检查，只含 ASCII 字体、数字、图标与 L/R/A/B 控制标签，没有独立英文词语。ASCII 字体表不应替换，否则会影响引擎兼容。
- ChiliBite 开发者商标、ANGUNA 品牌和图标保留。

字体资源来自 POWDER 工作区中已有的 Fusion Pixel BDF；本目录 `assets/fonts/OFL.txt` 与 `SOURCE.md` 保留来源和许可。

限制：这里完成的是资源编码和像素一致性验证，选项切换/结束流程还需由主任务在最终 ROM 的模拟器运行验证。
