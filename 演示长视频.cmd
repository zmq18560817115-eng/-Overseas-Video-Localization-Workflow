@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  长视频演示：5镜分镜 + 拼接成片（约15-30分钟）
echo  产品：便携恒温杯 · 场景：夜间卧室喂奶
echo.

powershell -NoProfile -Command "try { (Invoke-WebRequest -Uri 'http://127.0.0.1:8788/api/health' -UseBasicParsing -TimeoutSec 2) | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
  start "本地化工作台" cmd /k "cd /d "%~dp0海外视频本地化MVP" && call 启动页面.cmd"
  timeout /t 8 /nobreak >nul
)

cd /d "%~dp0overseas-loc-mvp"
"..\\海外视频本地化MVP\\.venv\\Scripts\\python.exe" -m pip install -q imageio-ffmpeg 2>nul
cd /d "%~dp0海外视频本地化MVP"
".venv\Scripts\python.exe" scripts\demo_long_video.py
pause
