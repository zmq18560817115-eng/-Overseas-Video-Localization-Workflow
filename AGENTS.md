# Agent 指引

## 海外视频本地化工作流

日常入口：`启动工作台.cmd` → http://127.0.0.1:8788

### 出稿规范 Skill（必用）

路径：`overseas-video-output-standards/`

生成或审核脚本、分镜、SeedDance、成片时，遵循该 skill 及 `.cursor/rules/overseas-video-output-standards.mdc`。

### 目录

| 目录 | 用途 |
|------|------|
| `01_素材库/` | 竞品对标、产品资料、脚本快照 |
| `03_产出库/` | 版本化视频归档（不覆盖历史） |
| `04_成稿库/` | 交付索引 |
| `overseas-loc-mvp/runs/` | 当前工作副本 |

### 验证

```powershell
cd 海外视频本地化MVP
.\.venv\Scripts\python.exe scripts\validate_output_standards_skill.py
```
