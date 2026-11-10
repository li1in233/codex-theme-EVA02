@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Update.ps1" %*
set "EVA_UPDATE_EXIT=%ERRORLEVEL%"
if not "%EVA_UPDATE_EXIT%"=="0" echo Update failed. Please read the error above.
pause
exit /b %EVA_UPDATE_EXIT%
