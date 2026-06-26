@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  海外视频本地化 · 端到端测试
echo  ─────────────────────────────────────
echo  流程：素材 -^> 脚本 -^> 交付 -^> SeedDance 空镜 -^> zip
echo  需已运行：启动工作台.cmd（8788）
echo  需已配置：overseas-loc-mvp\.env 的 ARK_API_KEY
echo.

powershell -NoProfile -Command "try { (Invoke-WebRequest -Uri 'http://127.0.0.1:8788/api/health' -UseBasicParsing -TimeoutSec 2) | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
  echo  [提示] 8788 未启动，正在打开工作台…
  start "本地化工作台" cmd /k "cd /d "%~dp0海外视频本地化MVP" && call 启动页面.cmd"
  echo  等待 8 秒后自动继续…
  timeout /t 8 /nobreak >nul
)

cd /d "%~dp0海外视频本地化MVP"
".venv\Scripts\python.exe" scripts\walkthrough_check.py --with-seedance
set ERR=%ERRORLEVEL%
echo.
if %ERR%==0 (
  echo  测试通过。请到 成稿库 或 runs\ref-xxx\broll\ 查看 mp4
) else (
  echo  部分步骤失败，请查看上方 [FAIL] 行
)
pause
exit /b %ERR%
