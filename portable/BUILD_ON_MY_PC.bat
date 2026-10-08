@echo off
rem Run this ONCE on a Windows PC with internet. It builds the folder you copy to the USB stick.
setlocal
cd /d "%~dp0"
set PYVER=3.12.8
set OUT=%~dp0..\calculator_portable
echo Building into %OUT%
if exist "%OUT%" rmdir /s /q "%OUT%"
mkdir "%OUT%\python"
echo Downloading Python %PYVER% embeddable...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri https://www.python.org/ftp/python/%PYVER%/python-%PYVER%-embed-amd64.zip -OutFile '%TEMP%\pyembed.zip'"
if errorlevel 1 goto fail
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Force '%TEMP%\pyembed.zip' '%OUT%\python'"
if errorlevel 1 goto fail
rem The embeddable distribution starts in ISOLATED mode: python312._pth alone
rem decides sys.path, the script directory is NOT added, and CWD is ignored.
rem Without the '..' line below, `import engine` and `import mvp_server` both
rem fail with ModuleNotFoundError for every entry point except launcher.py.
rem Paths in a _pth file are resolved relative to the _pth file's own folder,
rem so '..' is the application folder that holds mvp_server.py and engine\.
echo Patching python312._pth to expose the application folder...
>"%OUT%\python\python312._pth" echo python312.zip
>>"%OUT%\python\python312._pth" echo .
>>"%OUT%\python\python312._pth" echo ..
>>"%OUT%\python\python312._pth" echo(
>>"%OUT%\python\python312._pth" echo # Uncomment to run site.main() automatically
>>"%OUT%\python\python312._pth" echo #import site
if not exist "%OUT%\python\python312._pth" goto fail
echo Copying app files...
set SRC=%~dp0..
copy "%SRC%\mvp_server.py" "%OUT%\" >nul || goto fail
copy "%SRC%\frontend.html" "%OUT%\" >nul || goto fail
copy "%~dp0launcher.py" "%OUT%\" >nul || goto fail
copy "%~dp0RUN_CALCULATOR.bat" "%OUT%\" >nul || goto fail
copy "%~dp0README_FOR_TEACHER.txt" "%OUT%\" >nul || goto fail
xcopy "%SRC%\engine" "%OUT%\engine\" /E /I /Q /Y >nul || goto fail
xcopy "%SRC%\katex" "%OUT%\katex\" /E /I /Q /Y >nul || goto fail
xcopy "%SRC%\ClassWizFontSet" "%OUT%\ClassWizFontSet\" /E /I /Q /Y >nul || goto fail
if exist "%SRC%\raw" xcopy "%SRC%\raw" "%OUT%\raw\" /E /I /Q /Y >nul
for /d /r "%OUT%" %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
echo.
echo Verifying the build with the bundled Python (no system Python)...
pushd "%OUT%"
"%OUT%\python\python.exe" -u -c "import mvp_server; mvp_server.run_startup_selftest()"
set VERIFYRC=%ERRORLEVEL%
popd
if not "%VERIFYRC%"=="0" goto fail
echo.
echo BUILD VERIFIED: bundled Python imported the real engine.
echo.
echo DONE. Copy the folder calculator_portable to the USB stick.
pause
exit /b 0
:fail
echo.
echo BUILD FAILED. Take a screenshot of this window.
pause
exit /b 1
