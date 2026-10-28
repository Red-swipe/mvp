@echo off
setlocal
cd /d "%~dp0"
title Mentis ClassWiz Calculator
set "PYTHON="
if exist "%~dp0python\python.exe" set "PYTHON=%~dp0python\python.exe"
if not defined PYTHON for %%V in (3.11 3.12 3.13) do if not defined PYTHON py -%%V -c "import sys" >nul 2>&1 && set "PYTHON=py -%%V"
if not defined PYTHON python -c "import sys; assert sys.version_info >= (3,11)" >nul 2>&1 && set "PYTHON=python"
if not defined PYTHON (
 echo ERROR: Python 3.11 or newer was not found. Install Python from python.org or rebuild with BUILD_ON_MY_PC.bat.
 if not "%CASIO_NO_PAUSE%"=="1" pause
 exit /b 1
)
%PYTHON% "%~dp0launcher.py"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" echo Calculator exited with error %RC%. See calculator_log.txt for details.
if not "%CASIO_NO_PAUSE%"=="1" pause
exit /b %RC%
