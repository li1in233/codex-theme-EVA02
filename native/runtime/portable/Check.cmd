@echo off
setlocal
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install.ps1" -CheckOnly %*
set "EVA_CHECK_EXIT=%ERRORLEVEL%"
echo.
pause
exit /b %EVA_CHECK_EXIT%
