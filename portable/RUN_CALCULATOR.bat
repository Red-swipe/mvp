@echo off
title Calculator
cd /d "%~dp0"
if not exist "python\python.exe" (
  echo Python folder is missing. Please copy the WHOLE folder, not just this file.
  pause
  exit /b 1
)
rem -u keeps the startup self-test output unbuffered so the [SELFTEST] report is
rem visible immediately even when output is redirected to a file.
"python\python.exe" -u launcher.py
if errorlevel 1 pause
