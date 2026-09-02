@echo off
title Excel Files Merger
echo ======================================================
echo           Excel Sheets and Files Merger
echo ======================================================
echo.
python "%~dp0merge_excel.py" %*
echo.
pause
