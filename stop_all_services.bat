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

:: 2. Terminate background servers (ports 8000, 8080, 8090, 8501, 8502)
echo [2/2] Terminating servers on ports 8000, 8080, 8090, 8501 (ML EDA), 8502 (Agent UI)...
taskkill /F /IM llama-server.exe >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8090" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8080" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8501" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8502" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo ===============================================================================
echo   ALL SERVICES STOPPED SUCCESSFULLY.
echo   - Ports 8000, 8080, 8090, 8501, 8502 released.
echo ===============================================================================
echo.
pause
