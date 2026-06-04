@echo off
REM Windows 启动脚本 - 同时启动前后端
REM 双击运行或在 cmd 中运行: start_all.bat

echo =============================================
echo   走起 GoNow - 启动前后端服务
echo =============================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未找到 Python，请先安装 Python
    pause
    exit /b 1
)

REM 启动
python start_all.py

pause
