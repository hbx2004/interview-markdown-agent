@echo off
setlocal
cd /d "%~dp0"

if not exist "%~dp0frontend\node_modules" (
    echo Installing frontend dependencies...
    call npm install --prefix "%~dp0frontend"
)

start "Interview Backend" cmd /k "cd /d "%~dp0backend\scripts" && dev.bat"
start "Interview Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

