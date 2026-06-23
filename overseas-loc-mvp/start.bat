@echo off
chcp 65001 >nul
echo 该目录现在作为内部交付引擎，不再单独启动页面。
echo 正在打开统一工作台 http://127.0.0.1:8788
call "%~dp0..\启动工作台.cmd"
