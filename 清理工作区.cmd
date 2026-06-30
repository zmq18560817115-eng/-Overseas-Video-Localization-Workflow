@echo off
setlocal
cd /d "%~dp0"
"海外视频本地化MVP\.venv\Scripts\python.exe" "海外视频本地化MVP\scripts\cleanup_workspace.py" %*
exit /b %ERRORLEVEL%
