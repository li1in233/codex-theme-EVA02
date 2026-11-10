@echo off
setlocal
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Collect-Diagnostics.ps1" %*
set "EVA_DIAGNOSTICS_EXIT=%ERRORLEVEL%"
echo.
if not "%EVA_DIAGNOSTICS_EXIT%"=="0" echo Collection failed. Please read the error above.
pause
exit /b %EVA_DIAGNOSTICS_EXIT%
