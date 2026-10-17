# Anguna: Warriors of Virtue 简体中文汉化

对 GBA 自制游戏 *Anguna: Warriors of Virtue* 的简体中文补丁。原始 ROM 保持不变，成品为 `output/anguna_zh.gba` 与对应 BPS 补丁。

原版 SHA-256：`1df5a07fef92a526768333d041eec42d4efabfba1ad50e347b8146954ed07ff5`

## 汉化范围

- 224 条游戏文本：剧情、菜单、物品、地图名称、敌人资料与结局。
- 标题画面和结束画面图片一并重绘；作者姓名与 ANGUNA 品牌保留原样。
- 开场三页与结局七行旁白使用 Fusion Pixel 12px 简体点阵，保留暗色阴影；结局按 16px 行高滚动。
- 其他界面使用 8px 点阵字以适配原版布局。

## 使用

- 直接运行 `output/anguna_zh.gba`。
- 或把 `output/anguna_zh.bps` 应用到完全相同的原版 ROM。

## 验证

- mGBA 验证正常开场、菜单、全部译文与字体图块、结局滚动。
- 四个商店、30 种敌人资料及肖像、结束画面均经检查（后期场景用模拟器 RAM 调度）。
- BPS 补丁已回放验证，原 ROM 未改动。
- 不是完整通关测试，尚未在实机验证；存档往返测试未确认，建议测试时备份存档。

## 目录

- `analysis/`：字形、图形、运行时检查与覆盖率记录。
- `assets/`：汉化使用的字体与图形资源。
- `build/`：构建中间产物（不提交）。
- `licenses/`：游戏源码 MIT 授权与字体 SIL OFL 1.1 授权。
- `original/`：原始 ROM（不提交）。
- `output/`：可用 ROM、BPS 与截图。
- `tools/`：构建与校验脚本。
- `translations/`：译文源文件。

构建代码位于 `tools/`，译文位于 `translations/`。
