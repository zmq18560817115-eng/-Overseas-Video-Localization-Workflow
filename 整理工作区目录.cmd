@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  整理工作区：迁移素材库目录 + 归档已有成片到 03_产出库
echo  （保留 runs 内旧视频，不删除）
echo.
cd /d "%~dp0海外视频本地化MVP"
if not exist ".venv\Scripts\python.exe" (
  echo [失败] 请先运行「安装并检查开发环境.cmd」
  pause
  exit /b 1
)
".venv\Scripts\python.exe" scripts\migrate_workspace_layout.py
pause
