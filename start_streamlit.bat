@echo off
title ESP APM — Agent Streamlit Launcher
color 0B

echo ===============================================================================
echo   ESP APM — AGENT STREAMLIT OPERATIONS CENTER LAUNCHER
echo ===============================================================================
echo.

cd /d "%~dp0"

:: 1. Check Python
if exist "esp_agent\.venv\Scripts\python.exe" (
    set "PY_EXEC=%~dp0esp_agent\.venv\Scripts\python.exe"
) else (
    set "PY_EXEC=python"
)

:: 2. Start cced_esp Backend REST Service (:8000)
echo [1/3] Checking cced_esp Backend REST Server on port 8000...
start "ESP Platform - cced_esp Backend (:8000)" cmd /k "cd /d %~dp0cced_esp && %PY_EXEC% -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"

:: 3. Start Local CUDA GPU LLM Server (:8080)
echo [2/3] Checking Local CUDA GPU LLM Server on port 8080...
start "ESP Platform - Local GPU LLM (:8080)" cmd /k "cd /d %~dp0 && call start_gpu_llm.bat"

:: 4. Start Agent Streamlit Operations Center (:8501)
echo [3/3] Launching Agent Streamlit on port 8501...
timeout /t 3 /nobreak >nul
start "ESP Platform - Agent Streamlit UI (:8501)" cmd /k "cd /d %~dp0 && python -m streamlit run agent_streamlit.py"

echo.
echo ===============================================================================
echo   SERVICES LAUNCHED!
echo   - Agent Streamlit UI : http://localhost:8501
echo   - cced_esp Backend   : http://localhost:8000/docs
echo   - Local GPU LLM      : http://localhost:8080/v1
echo ===============================================================================
echo.
pause
