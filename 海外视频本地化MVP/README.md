# 海外视频本地化 MVP · 竞品采集与工作台

**TikTok 竞品元数据 → 结构拆解 → 脚本生成 → 交付 zip**

日常入口：根目录 **`启动工作台.cmd`** → http://127.0.0.1:8788

## 用户流程（5 步）

素材库 → 脚本生成（产品 + 标签 + 生成）→ 完成交付 → 成稿库 / 反馈库

| 环节 | 引擎 |
|------|------|
| 同步 TikTok | oEmbed + Playwright |
| 结构拆解 | 规则模板（标题/话题） |
| 生成脚本 | Claude（`ANTHROPIC_API_KEY`）或规则模板 |
| 完成交付 | `overseas-loc-mvp` 子进程 |
| AI 空镜 | SeedDance 2.0 / fal.ai（`FAL_KEY`，可选） |

## 命令行（设置页可代替）

```bat
运行.cmd fetch
运行.cmd decompose      :: 结构拆解 → video_analysis
运行.cmd templates
运行.cmd products
运行.cmd bridge --id 19
```

## 目录

```
海外视频本地化MVP/
├── 启动页面.cmd          # 开发用，由 启动工作台.cmd 调用
├── .env.example
├── 数据表/               # CSV 数据源
├── web/                  # 8788 前端
├── app/                  # 8788 后端
└── scripts/pipeline.py
```

知识库配置：根目录 `config/knowledge-sources.json`
