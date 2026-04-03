@echo off
REM Run backend test suite
REM hash-salt 1
setlocal
cd /d "%~dp0.."
powershell -ExecutionPolicy Bypass -File ".\scripts\backend.ps1" test
pause
