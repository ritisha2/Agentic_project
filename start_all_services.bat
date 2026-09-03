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
echo [2/5] Initializing Database Schemas ^& Knowledge Graphs...
%PY_EXEC% esp_agent\scripts\init_db.py >nul 2>&1
%PY_EXEC% esp_agent\scripts\seed_db.py >nul 2>&1
%PY_EXEC% esp_agent\scripts\seed_neo4j.py >nul 2>&1
%PY_EXEC% esp_agent\scripts\seed_qdrant.py >nul 2>&1
echo [+] Neo4j, Qdrant ^& PostgreSQL verified and seeded.
echo.

:: 4. Start Local CUDA GPU LLM Server (:8080)
echo [3/6] Starting Local CUDA GPU LLM Server on port 8080...
start "ESP Platform - Local GPU LLM (:8080)" cmd /k "cd /d %~dp0 && call start_gpu_llm.bat"

:: 5. Start cced_esp Backend REST Service (:8000)
echo [4/6] Starting cced_esp Backend REST Server on port 8000...
start "ESP Platform - cced_esp Backend (:8000)" cmd /k "cd /d %~dp0cced_esp && %PY_EXEC% -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"

:: 6. Start esp_agent Gateway BFF Service (:8090)
echo [5/6] Starting esp_agent Gateway BFF Server on port 8090...
start "ESP Platform - esp_agent Gateway (:8090)" cmd /k "cd /d %~dp0esp_agent && %PY_EXEC% -m uvicorn src.api.rest.gateway:app --host 0.0.0.0 --port 8090"

:: 7. Start ML Analytics & EDA Streamlit Dashboard (:8501)
echo [6/6] Starting ML Analytics ^& EDA Dashboard on port 8501...
start "ESP Platform - ML EDA Dashboard (:8501)" cmd /k "cd /d %~dp0 && %PY_EXEC% -m streamlit run code/eda/dashboard.py --server.port 8501"

:: 8. Start Agent Streamlit Operations Center (:8502)
echo [7/7] Starting Agent Streamlit Operations Center on port 8502...
start "ESP Platform - Agent Streamlit UI (:8502)" cmd /k "cd /d %~dp0 && %PY_EXEC% -m streamlit run agent_streamlit.py --server.port 8502"

:: Wait 4 seconds for servers to bind
echo Waiting 4 seconds for services to initialize...
timeout /t 4 /nobreak >nul
echo.

:: Probe & Print Full Health Matrix
echo Probing all Database ^& Application Services...
%PY_EXEC% run_all_services.py --status

echo.
echo ===============================================================================
echo   ALL SERVICES ARE INITIALIZED!
echo   - ML EDA Dashboard   : http://localhost:8501
echo   - Agent Streamlit UI : http://localhost:8502
echo   - cced_esp API Docs  : http://localhost:8000/docs
echo   - esp_agent API Docs : http://localhost:8090/docs
echo   - Local GPU LLM      : http://localhost:8080/v1
echo   - Neo4j Browser      : http://localhost:7474 (neo4j / password123)
echo   - Qdrant Dashboard   : http://localhost:6333/dashboard
echo ===============================================================================
echo.
pause
