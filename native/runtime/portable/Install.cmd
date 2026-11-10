@echo off
setlocal
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install.ps1" %*
set "EVA_INSTALL_EXIT=%ERRORLEVEL%"
echo.
if not "%EVA_INSTALL_EXIT%"=="0" echo Installation failed. Please read the error above.
pause
exit /b %EVA_INSTALL_EXIT%
