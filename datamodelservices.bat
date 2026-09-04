@echo off
setlocal enabledelayedexpansion

:: =============================================================================
:: ESP APM PLATFORM — DATA MODEL & KNOWLEDGE SERVICES ORCHESTRATOR
:: =============================================================================
:: Manages background containerized & mock services:
::   1. PostgreSQL / pgvector   :5432   (Document Chunks, Embeddings, Relational Tables)
::   2. Qdrant Vector DB        :6333   (Semantic Search, Cosine Similarity Index)
::   3. Neo4j Graph DB          :7687   (Ontology Causal Graph, Cypher Queries, HTTP :7474)
::   4. Redis Cache / Streams   :6379   (High-speed In-Memory KV & Event Streams)
::   5. Advait Asset API Mock   :8010   (Canonical Fleet Metadata, Tags, Well Specs)
:: =============================================================================

set ACTION=%1
if "%ACTION%"=="" set ACTION=start

if /i "%ACTION%"=="stop" goto do_stop
if /i "%ACTION%"=="down" goto do_stop
if /i "%ACTION%"=="status" goto do_status
if /i "%ACTION%"=="start" goto do_start
if /i "%ACTION%"=="up" goto do_start

echo [ERROR] Unknown action: %ACTION%
echo Usage: datamodelservices.bat [start ^| stop ^| status]
exit /b 1

:do_start
cls
echo =============================================================================
echo   STARTING ESP DATA MODEL & KNOWLEDGE BASE SERVICES
echo =============================================================================
echo.

where docker >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Docker not found in PATH!
    echo Attempting standalone local Python start for Advait Asset Mock...
    goto start_python_fallback
)

echo [1/2] Launching Docker Compose Stack (Postgres, Qdrant, Neo4j, Redis, Advait Mock)...
docker compose -f esp_agent\docker-compose.yml up -d
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Docker compose failed or Docker daemon not running.
    echo Trying fallback for local Advait Asset Mock...
    goto start_python_fallback
)

echo.
echo [2/2] Waiting 5 seconds for service initialization...
timeout /t 5 /nobreak >nul
goto show_banner

:start_python_fallback
echo.
echo Launching Advait Mock Asset API standalone via Uvicorn on port 8010...
start "Advait-Asset-API-8010" cmd /k "cd data\advait\advait_api_mock_service && python -m uvicorn app.main:app --host 0.0.0.0 --port 8010"
timeout /t 3 /nobreak >nul
goto show_banner

:do_stop
echo =============================================================================
echo   STOPPING ESP DATA MODEL & KNOWLEDGE BASE SERVICES
echo =============================================================================
echo.
where docker >nul 2>&1
if %ERRORLEVEL% equ 0 (
    docker compose -f esp_agent\docker-compose.yml down
    echo [OK] Docker containers stopped.
)
echo.
exit /b 0

:do_status
:show_banner
echo.
echo =============================================================================
echo   ESP DATA MODEL & KNOWLEDGE SERVICES — ACTIVE ENDPOINTS
echo =============================================================================
echo   Service Name              Port      Purpose / Function
echo   ------------------------  --------  ----------------------------------------
echo   PostgreSQL / pgvector     :5432     Doc Embeddings, Structured Tables
echo   Qdrant Vector DB          :6333     Semantic Vector Search Index
echo   Neo4j Graph DB (Bolt)     :7687     ESP Causal Graph (Web UI: http://localhost:7474)
echo   Redis Cache               :6379     Fast In-Memory State & PubSub
echo   Advait Asset API Mock     :8010     Asset Metadata & Topology (http://localhost:8010/api/v1)
echo =============================================================================
echo.
echo NOTE: Keep this stack LIVE when:
echo   - Running live ingestion of asset context
echo   - Running hybrid knowledge retrieval (vector + graph + documents)
echo.
echo To stop all data model services, run:
echo   datamodelservices.bat stop
echo =============================================================================
echo.
exit /b 0
