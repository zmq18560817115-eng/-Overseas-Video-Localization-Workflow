@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo  海外视频本地化工作台 - 内网服务器模式
echo  -------------------------------------
echo  监听 0.0.0.0:8788，局域网可访问
echo  TikTok 采集需在服务器桌面登录 Chrome
echo  登录态目录: tiktok_collector\data\browser_profile
echo.

set WORKBENCH_HOST=0.0.0.0
set WORKBENCH_PORT=8788
set WORKBENCH_LAUNCHER=server
set TIKTOK_COLLECTOR_SERVER_MODE=1
set PLAYWRIGHT_BROWSERS_PATH=

cd /d "%~dp0海外视频本地化MVP"
call 启动页面.cmd
