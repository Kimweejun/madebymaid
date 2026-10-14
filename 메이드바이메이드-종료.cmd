@echo off
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "%~dp0komow-local\Stop-Komow.ps1"
if errorlevel 1 pause
