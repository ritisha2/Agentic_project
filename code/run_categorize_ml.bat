@echo off
title CCED Well Categorization and ML Normalization
echo ======================================================
echo    CCED Well Categorization and ML Normalization
echo ======================================================
echo.
python "%~dp0categorize_and_normalize_ml.py" %*
echo.
pause
