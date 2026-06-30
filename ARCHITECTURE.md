# 本地部署架构（精简）

## 运行链路

```
启动工作台.cmd
  └─ 海外视频本地化MVP (8788) — UI + 素材/脚本/成稿/反馈 API
        ├─ 01_素材库 — 竞品 CSV、拆解、产品图、脚本快照
        ├─ 04_成稿库 / 05_反馈库 — 交付索引与闭环反馈
        ├─ 03_产出库 — 版本化成片归档
        └─ subprocess → overseas-loc-mvp — 字幕、zip、SeedDance、合规
              └─ runs/ref-{id}/ — 当前工作副本
```

## 必留目录

| 路径 | 作用 |
|------|------|
| `海外视频本地化MVP/` | 主工作台 + `.venv` |
| `overseas-loc-mvp/` | 交付引擎 + `.venv` + `runs/` + `.env` |
| `01_素材库/` | 全部业务素材与脚本快照 |
| `03_产出库/` | 历史成片版本 |
| `04_成稿库/` | 成稿索引 |
| `05_反馈库/` | 反馈闭环数据 |
| `overseas-video-output-standards/` | 出稿 Skill |
| `config/` | 知识库与豆包配置示例 |
| `tiktok_collector/` | TikTok 同步（可选） |

## 兼容联接（自动）

旧路径 `数据表/`、`成稿库/` 等为 **junction** 指向 `01_*` / `04_*` / `05_*`，启动 8788 时自动创建。

## 维护命令

| 命令 | 作用 |
|------|------|
| `启动工作台.cmd` | 日常入口 |
| `安装并检查开发环境.cmd` | 双 venv 与依赖 |
| `配置SeedDance.cmd` | 编辑 `overseas-loc-mvp/.env` |
| `整理工作区目录.cmd` | 首次迁移素材到 `01_*` |
| `python 海外视频本地化MVP/scripts/cleanup_workspace.py` | 本瘦身脚本 |
