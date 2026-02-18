@echo off
REM NyayLens Startup Script for Windows
REM Double-click this file to start the project

echo Starting NyayLens...
echo.

REM Get current directory and set Python path
set "PROJECT_DIR=%~dp0"
set "PYTHON_EXE=C:\Users\ISHA SAHAY\AppData\Local\Programs\Python\Python312\python.exe"

REM Start Backend Server
echo Starting Backend Server on http://localhost:8001...
start "NyayLens Backend" cmd /k "cd /d "%PROJECT_DIR%" && "%PYTHON_EXE%" -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8001"

REM Wait for backend to initialize
timeout /t 3 /nobreak >nul

REM Start Frontend Server  
echo Starting Frontend Server on http://localhost:5500...
start "NyayLens Frontend" cmd /k "cd /d "%PROJECT_DIR%frontend" && "%PYTHON_EXE%" -m http.server 5500 --bind 127.0.0.1"

REM Wait for frontend to be ready
timeout /t 2 /nobreak >nul

echo.
echo ===============================================
echo   NyayLens is running!
echo ===============================================
echo   Backend API: http://localhost:8001
echo   API Docs:    http://localhost:8001/docs
echo   Frontend:    http://localhost:5500
echo ===============================================
echo.

REM Open browser
start http://localhost:5500

echo Browser opened. Servers are running in separate windows.
echo Close those windows to stop the servers.
echo.
pause
