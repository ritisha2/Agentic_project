@echo off
title CCED VFD Time-Series EDA & Diagnostic Dashboard
echo ========================================================
echo   CCED VFD Time-Series EDA & Diagnostic Dashboard
echo ========================================================
echo.
echo Launching Streamlit Interactive Dashboard...
echo Local URL: http://localhost:8501
echo.
python -m streamlit run "%~dp0dashboard.py" --server.port 8501 --browser.gatherUsageStats false
pause
