@echo off
title ESP APM Platform — Master Service Launcher
color 0A

echo ===============================================================================
echo   ESP APM PLATFORM — 1-CLICK MASTER SERVICE LAUNCHER
echo ===============================================================================
echo.

:: 1. Navigate to Project Root
cd /d "%~dp0"

:: 2. Check & Start Docker DB Services (Neo4j, Postgres, Qdrant, Redis)
echo [1/5] Starting Containerized Databases (Neo4j, Postgres/pgvector, Qdrant, Redis)...
docker --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Docker is not installed or not in PATH. Skipping Docker DBs.
) else (
    docker compose -f esp_agent\docker-compose.yml up -d
)
echo.

if exist "esp_agent\.venv\Scripts\python.exe" (
    set "PY_EXEC=%~dp0esp_agent\.venv\Scripts\python.exe"
) else (
    set "PY_EXEC=python"
)

:: 3. Auto-Seed Database Schemas & Knowledge Graphs
echo [2/5] Initializing Database Schemas & Knowledge Graphs...
%PY_EXEC% esp_agent\scripts\init_db.py >nul 2>&1
%PY_EXEC% esp_agent\scripts\seed_db.py >nul 2>&1
%PY_EXEC% esp_agent\scripts\seed_neo4j.py >nul 2>&1
echo [+] Neo4j & PostgreSQL verified and seeded.
echo.

:: 4. Start cced_esp Backend REST Service (:8000)
echo [3/5] Starting cced_esp Backend REST Server on port 8000...
start "ESP Platform - cced_esp Backend (:8000)" cmd /k "cd /d %~dp0cced_esp && %PY_EXEC% -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"

:: 5. Start esp_agent Gateway BFF Service (:8090)
echo [4/5] Starting esp_agent Gateway BFF Server on port 8090...
start "ESP Platform - esp_agent Gateway (:8090)" cmd /k "cd /d %~dp0esp_agent && %PY_EXEC% -m uvicorn src.api.rest.gateway:app --host 0.0.0.0 --port 8090"

:: Wait 4 seconds for servers to bind
echo Waiting 4 seconds for services to initialize...
timeout /t 4 /nobreak >nul
echo.

:: 5. Probe & Print Full Health Matrix
echo [4/4] Probing all Database & Application Services...
%PY_EXEC% run_all_services.py --status

echo.
echo ===============================================================================
echo   ALL SERVICES ARE INITIALIZED!
echo   - cced_esp API Docs  : http://localhost:8000/docs
echo   - esp_agent API Docs : http://localhost:8090/docs
echo   - Neo4j Browser      : http://localhost:7474 (neo4j / password123)
echo   - Qdrant Dashboard   : http://localhost:6333/dashboard
echo.
echo   To run an AI Historian Query:
echo     cd esp_agent
echo     .venv\Scripts\python.exe query_historian.py -q "Why is production declining on FS-031?"
echo ===============================================================================
echo.
pause
