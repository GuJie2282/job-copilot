@echo off
echo ========================================
echo   求职 Copilot 前端项目启动脚本
echo ========================================
echo.

REM 检查 Node.js 是否安装
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未检测到 Node.js，请先安装 Node.js
    echo 下载地址: https://nodejs.org/
    pause
    exit /b 1
)

echo [1/4] 检测到 Node.js
node --version
npm --version
echo.

REM 进入前端目录
cd /d %~dp0
echo [2/4] 进入项目目录: %CD%
echo.

REM 检查 node_modules
if not exist "node_modules" (
    echo [3/4] 首次运行，正在安装依赖...
    echo 这可能需要几分钟，请耐心等待...
    echo.
    call npm install
    if %ERRORLEVEL% NEQ 0 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
    echo.
    echo [✓] 依赖安装完成
) else (
    echo [3/4] 依赖已存在，跳过安装
)
echo.

echo [4/4] 启动开发服务器...
echo.
echo ========================================
echo   服务器将在以下地址启动:
echo   http://localhost:3000
echo.
echo   按 Ctrl+C 可停止服务器
echo ========================================
echo.

call npm run dev

pause
