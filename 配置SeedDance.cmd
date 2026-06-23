@echo off
chcp 65001 >nul
cd /d "%~dp0overseas-loc-mvp"

echo.
echo  SeedDance 2.0 外接配置（fal.ai）
echo  ─────────────────────────────────────
echo  1. 打开 https://fal.ai/dashboard/keys 申请 API Key
echo  2. 在下面打开的 .env 里填写：  FAL_KEY=你的密钥
echo  3. 保存后运行本脚本里的测试
echo.

start notepad ".env"

echo 填好 FAL_KEY 并保存 notepad 后，按任意键测试连接...
pause >nul

".venv\Scripts\python.exe" scripts\test_seedance.py
if errorlevel 1 (
  echo.
  echo 测试失败：请检查 FAL_KEY 是否正确、网络是否可访问 fal.ai
  pause
  exit /b 1
)

echo.
echo 测试成功，正在重启 8788 工作台加载新配置...
cd /d "%~dp0"
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8788" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
timeout /t 1 /nobreak >nul
start "本地化工作台" cmd /k "cd /d ""%~dp0海外视频本地化MVP"" && call 启动页面.cmd"
timeout /t 4 /nobreak >nul
start "" "http://127.0.0.1:8788"
echo 已完成。
pause
