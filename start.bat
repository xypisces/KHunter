@echo off
chcp 65001 >nul
title KHunter - Start

cd /d "%~dp0"

:: Check uv
uv --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] uv not found. Install with: curl -LsSf https://astral.sh/uv/install.sh ^| sh
    pause
    exit /b 1
)

:: Start server
echo Starting KHunter with uv...
uv run web_server.py

pause
