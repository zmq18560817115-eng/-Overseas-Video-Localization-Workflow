@echo off
chcp 65001 >nul
pushd "%~dp0"

set "TARGET_DIR="
for /d %%D in ("%CD%\*") do (
  if exist "%%~fD\.venv\Scripts\python.exe" if exist "%%~fD\scripts\tiktok_workflow.py" set "TARGET_DIR=%%~fD"
)

if not defined TARGET_DIR (
  echo MVP directory not found under %CD%
  popd
  exit /b 1
)

cd /d "%TARGET_DIR%"

if not exist ".venv\Scripts\python.exe" (
  echo Python venv not found: %cd%\.venv\Scripts\python.exe
  popd
  exit /b 1
)

".venv\Scripts\python.exe" scripts\tiktok_workflow.py %*
set EXIT_CODE=%ERRORLEVEL%
popd
exit /b %EXIT_CODE%
