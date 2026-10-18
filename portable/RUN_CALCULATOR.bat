@echo off
rem ==============================================================================
rem Mentis ClassWiz Calculator Launcher (UNTESTED on Windows at runtime)
rem ==============================================================================
title Mentis ClassWiz Calculator

rem Ensure working directory is always the folder containing this .bat file
cd /d "%~dp0"

rem ---- log file selection ----------------------------------------------------
rem Each running instance holds its log file open exclusively for its whole
rem lifetime (see the launcher.py redirect below). A second launch from this
rem same folder therefore CANNOT write to launcher.log at all: every redirect
rem fails with "The process cannot access the file because it is being used by
rem another process." and the instance dies before the server starts.
rem
rem Appending (>>) is therefore NOT sufficient. Instead every instance writes
rem its OWN log: the first keeps the historical launcher.log, later ones get
rem launcher-2.log, launcher-3.log and so on. free_port() already scans
rem 8000-8049, so the extra instances simply come up on 8001, 8002, ...
set LOGFILE="%~dp0launcher.log"
if not exist %LOGFILE% goto :logready
set N=2
:findfree
if not exist "%~dp0launcher-%N%.log" goto :useit
set /a N+=1
goto findfree
:useit
set LOGFILE="%~dp0launcher-%N%.log"
:logready

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
    echo Details have been saved in the launcher log in this folder.
    echo Please email that log to support/your teacher for assistance.
    echo ==============================================================================
    echo.
    pause
    goto :EOF
)