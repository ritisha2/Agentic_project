@echo off
title ESP APM Platform — Stop All Services
color 0C

echo ===============================================================================
echo   ESP APM PLATFORM — STOPPING ALL SERVICES
echo ===============================================================================
echo.

cd /d "%~dp0"

:: 1. Stop Docker Containers
echo [1/2] Stopping Docker DB Containers (Neo4j, Postgres, Qdrant, Redis)...
docker --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    docker compose -f esp_agent\docker-compose.yml down
) else (
    echo [INFO] Docker not active.
)

:: 2. Terminate background Python uvicorn servers (port 8000 and port 8090)
echo [2/2] Terminating background uvicorn servers on ports 8000 and 8090...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8090" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo ===============================================================================
echo   ALL SERVICES STOPPED SUCCESSFULLY.
echo ===============================================================================
echo.
pause
