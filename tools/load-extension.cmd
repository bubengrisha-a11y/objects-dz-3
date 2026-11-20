@echo off
rem Wrapper: runs load-extension.ps1 with the given parameters.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0load-extension.ps1" %*
if errorlevel 1 (echo FAILED, see tools\load-extension.log) else (echo OK)
pause
