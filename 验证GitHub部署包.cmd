@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  验证 GitHub 部署包完整性
echo  ─────────────────────────────────────
echo  用于 git clone / git pull 后确认仓库可内网部署
echo.

set PY=%~dp0海外视频本地化MVP\.venv\Scripts\python.exe
if not exist "%PY%" (
  where python >nul 2>&1
  if errorlevel 1 (
    echo  未找到 Python，请先运行「检查开发环境.cmd」
    pause
    exit /b 1
  )
  set PY=python
)

"%PY%" "%~dp0海外视频本地化MVP\scripts\verify_deploy_repo.py"
set ERR=%ERRORLEVEL%
echo.
if %ERR% neq 0 (
  echo  校验未通过，请勿启动内网服务，先联系开发者补推 GitHub。
) else (
  echo  校验通过，可继续「部署内网.cmd」。
)
pause
exit /b %ERR%
