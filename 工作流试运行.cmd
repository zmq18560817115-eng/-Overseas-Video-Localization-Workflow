@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  工作流试运行（脚本分镜视频，默认每次最多 2 镜）
echo  ─────────────────────────────────────
echo  素材 -^> 脚本(5镜AI_VIDEO) -^> 交付+分镜视频 -^> 成稿库
echo  配置见 overseas-loc-mvp\.env 的 AI_VIDEO_MODE / MAX_SHOTS
echo.

powershell -NoProfile -Command "try { (Invoke-WebRequest -Uri 'http://127.0.0.1:8788/api/health' -UseBasicParsing -TimeoutSec 2) | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
  echo  [启动] 8788 未运行，正在打开工作台…
  start "本地化工作台" cmd /k "cd /d "%~dp0海外视频本地化MVP" && call 启动页面.cmd"
  timeout /t 8 /nobreak >nul
)

cd /d "%~dp0海外视频本地化MVP"
".venv\Scripts\python.exe" scripts\walkthrough_check.py
set ERR=%ERRORLEVEL%
echo.
if %ERR%==0 (
  echo  试运行通过。请刷新浏览器 http://127.0.0.1:8788 查看素材库
) else (
  echo  部分步骤失败，见上方 [FAIL]
)
pause
exit /b %ERR%
