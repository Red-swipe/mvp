@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
set "PYTHON="
for %%V in (3.11 3.12 3.13) do if not defined PYTHON py -%%V -c "import sys" >nul 2>&1 && set "PYTHON=py -%%V"
if not defined PYTHON python -c "import sys; assert sys.version_info >= (3,11)" >nul 2>&1 && set "PYTHON=python"
if not defined PYTHON (
 echo ERROR: Python 3.11 or newer is required to build the portable release.
 pause
 exit /b 1
)
set "PYVER=3.12.8"
set "WORK=%TEMP%\classwiz-build-%RANDOM%-%RANDOM%"
set "ZIP=%WORK%\python-embed.zip"
set "RUNTIME=%WORK%\python"
mkdir "%WORK%" || goto fail
mkdir "%RUNTIME%" || goto fail
echo Downloading CPython %PYVER% embeddable runtime...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/%PYVER%/python-%PYVER%-embed-amd64.zip' -OutFile '%ZIP%'"
if errorlevel 1 goto fail
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath '%ZIP%' -DestinationPath '%RUNTIME%' -Force"
if errorlevel 1 goto fail
%PYTHON% scripts\build_release.py --python-runtime "%RUNTIME%" --require-python
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" goto fail
rmdir /s /q "%WORK%"
echo.
echo Release ZIP created at dist\calculator_portable.zip
pause
exit /b 0
:fail
echo.
echo ERROR: Portable ZIP build failed. Temporary files: "%WORK%"
pause
exit /b 1
