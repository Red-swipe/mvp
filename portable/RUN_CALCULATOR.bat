@echo off
rem ==============================================================================
rem Mentis ClassWiz Calculator Launcher (UNTESTED on Windows at runtime)
rem ==============================================================================
title Mentis ClassWiz Calculator

rem Ensure working directory is always the folder containing this .bat file
cd /d "%~dp0"

rem Set log file path
set LOGFILE="%~dp0launcher.log"
echo [LAUNCHER] Starting ClassWiz Calculator... > %LOGFILE%
echo [LAUNCHER] Date/Time: %DATE% %TIME% >> %LOGFILE%
echo [LAUNCHER] Directory: "%~dp0" >> %LOGFILE%

rem Verify python executable presence
if not exist "%~dp0python\python.exe" (
    echo [ERROR] Python folder is missing at "%~dp0python\python.exe". >> %LOGFILE%
    echo.
    echo ==============================================================================
    echo ERROR: Python runtime folder is missing!
    echo Please copy the ENTIRE application folder, not just RUN_CALCULATOR.bat.
    echo ==============================================================================
    echo.
    pause
    goto :EOF
)

rem Launch launcher.py using unbuffered python (-u)
"%~dp0python\python.exe" -u "%~dp0launcher.py" >> %LOGFILE% 2>&1
if errorlevel 1 (
    echo [ERROR] Calculator exited with error level %ERRORLEVEL%. >> %LOGFILE%
    echo.
    echo ==============================================================================
    echo ERROR: The calculator failed to start or exited unexpectedly.
    echo Details have been saved to launcher.log in this folder.
    echo Please email launcher.log to support/your teacher for assistance.
    echo ==============================================================================
    echo.
    pause
    goto :EOF
)
