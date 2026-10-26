@echo off
setlocal

rem Always run from the repository root, no matter where this file was launched from.
cd /d "%~dp0"

rem Prefer a local virtual environment when one exists.
set "VENV_ACTIVATE="
if exist "venv\Scripts\activate.bat" set "VENV_ACTIVATE=venv\Scripts\activate.bat"
if not defined VENV_ACTIVATE if exist ".venv\Scripts\activate.bat" set "VENV_ACTIVATE=.venv\Scripts\activate.bat"

if defined VENV_ACTIVATE (
    echo Activating virtual environment: %VENV_ACTIVATE%
    call "%VENV_ACTIVATE%"
) else (
    echo [WARNING] No virtual environment found ^(venv\Scripts\activate.bat or .venv\Scripts\activate.bat^).
    echo [WARNING] Continuing with the system Python.
)

rem Locate the server entrypoint: root, then backend\, then server\.
set "SERVER_DIR="
if exist "mvp_server.py" set "SERVER_DIR=."
if not defined SERVER_DIR if exist "backend\mvp_server.py" set "SERVER_DIR=backend"
if not defined SERVER_DIR if exist "server\mvp_server.py" set "SERVER_DIR=server"

if not defined SERVER_DIR (
    echo [ERROR] mvp_server.py was not found in the repository root, backend\, or server\.
    echo [ERROR] Make sure this run.bat is in the repository root.
    pause
    exit /b 1
)

rem The server reads its own host/port defaults from mvp_server.py; do not hardcode them here.
echo Starting ClassWiz server from "%SERVER_DIR%" ...
pushd "%SERVER_DIR%"
python mvp_server.py
set "EXIT_CODE=%ERRORLEVEL%"
popd

if not "%EXIT_CODE%"=="0" echo [ERROR] Server exited with code %EXIT_CODE%.
echo.
echo Server stopped. Press any key to close this window.
pause >nul
exit /b %EXIT_CODE%
