# NyayLens Startup Script
# Run this script to start both backend and frontend servers

Write-Host "Starting NyayLens..." -ForegroundColor Green

# Get current directory
$projectPath = $PSScriptRoot
$pythonExe = "C:\Users\ISHA SAHAY\AppData\Local\Programs\Python\Python312\python.exe"

# Start Backend Server (FastAPI)
Write-Host "`nStarting Backend Server on http://localhost:8001..." -ForegroundColor Cyan
$backendCmd = "cd '$projectPath'; & '$pythonExe' -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8001"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

# Wait a bit for backend to start
Start-Sleep -Seconds 3

# Start Frontend Server
Write-Host "Starting Frontend Server on http://localhost:5500..." -ForegroundColor Cyan
$frontendCmd = "cd '$projectPath\frontend'; & '$pythonExe' -m http.server 5500 --bind 127.0.0.1"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

# Wait for servers to be ready
Start-Sleep -Seconds 2

Write-Host "`n✅ NyayLens is running!" -ForegroundColor Green
Write-Host "   Backend API: http://localhost:8001" -ForegroundColor Yellow
Write-Host "   API Docs: http://localhost:8001/docs" -ForegroundColor Yellow
Write-Host "   Frontend: http://localhost:5500" -ForegroundColor Yellow
Write-Host "`nOpening frontend in browser..." -ForegroundColor Cyan

# Open browser
Start-Process "http://localhost:5500"

Write-Host "`nPress any key to exit (this will NOT stop the servers)..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
