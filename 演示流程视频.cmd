@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  流程演示：脚本分镜 + Ark 短视频
echo  ─────────────────────────────────────

powershell -NoProfile -Command "try { (Invoke-WebRequest -Uri 'http://127.0.0.1:8788/api/health' -UseBasicParsing -TimeoutSec 2) | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
  echo  正在启动 8788 工作台…
  start "本地化工作台" cmd /k "cd /d "%~dp0海外视频本地化MVP" && call 启动页面.cmd"
  timeout /t 8 /nobreak >nul
)

cd /d "%~dp0海外视频本地化MVP"
".venv\Scripts\python.exe" scripts\demo_flow_video.py
pause
