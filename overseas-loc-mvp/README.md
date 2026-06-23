# 内部交付引擎

由 8788 工作台在后台调用，负责英文稿、字幕、交付 zip 与 SeedDance。无需单独打开页面。

**交付 zip**：`交付脚本包.md/json` + `subtitles.srt` + `剪辑单.html`（+ SeedDance 空镜如有）

启动：只需双击根目录 `启动工作台.cmd`  
完整说明见仓库根目录 `README_使用说明.md`

配置：复制 `.env.example` → `.env`，填写 `FAL_KEY`（SeedDance）
