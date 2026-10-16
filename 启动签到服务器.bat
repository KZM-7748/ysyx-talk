@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo   一生一芯签到抽奖服务器
echo ========================================
echo.
python server.py
pause
