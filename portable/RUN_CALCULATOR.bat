@echo off
setlocal
cd /d "%~dp0"
title Mentis ClassWiz Calculator
set "PYTHON="
set "PYTHON_ARGS="
if exist "%~dp0python\python.exe" goto bundled
for %%V in (3.11 3.12 3.13) do call :try_py %%V
if defined PYTHON goto launch
python -c "import sys; assert sys.version_info >= (3,11)" >nul 2>&1
if not errorlevel 1 set "PYTHON=python"
if defined PYTHON goto launch
echo ERROR: Python 3.11 or newer was not found. Install Python from python.org or rebuild with BUILD_ON_MY_PC.bat.
if not "%CASIO_NO_PAUSE%"=="1" pause
exit /b 1
:bundled
set "PYTHON=%~dp0python\python.exe"
goto launch
:try_py
if defined PYTHON exit /b 0
py -%1 -c "import sys" >nul 2>&1
if not errorlevel 1 (
 set "PYTHON=py"
 set "PYTHON_ARGS=-%1"
)
exit /b 0
:launch
"%PYTHON%" %PYTHON_ARGS% "%~dp0launcher.py"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" echo Calculator exited with error %RC%. See calculator_log.txt for details.
if not "%CASIO_NO_PAUSE%"=="1" pause
exit /b %RC%
