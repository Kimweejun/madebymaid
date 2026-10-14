@echo off
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "%~dp0komow-local\Start-Komow.ps1"
if errorlevel 1 pause
