# NitA System Startup Script
# Starts both Backend (Flask) and Frontend (HTTP Server) simultaneously

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║      NitA AI-Powered Smart Food Waste Management System       ║" -ForegroundColor Cyan
Write-Host "║              Automated Startup (Requires Two Terminals)       ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$projectRoot = "f:\Code Playground\NitA\updated1\NitA"
$backendDir = "$projectRoot\backend"
$frontendDir = "$projectRoot\frontend"
$pythonExe = "$projectRoot\.venv\Scripts\python.exe"

Write-Host "Project Root: $projectRoot" -ForegroundColor Gray
Write-Host "Python Executable: $pythonExe" -ForegroundColor Gray
Write-Host ""

# Check if Python exists
if (-not (Test-Path $pythonExe)) {
    Write-Host "ERROR: Python executable not found at $pythonExe" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Python venv found" -ForegroundColor Green
Write-Host ""

Write-Host "STARTING BACKEND AND FRONTEND SERVERS..." -ForegroundColor Yellow
Write-Host ""

# Kill any existing processes on ports 5000 and 8000
Write-Host "Cleaning up any existing processes on ports 5000 and 8000..." -ForegroundColor Gray
$processes = netstat -ano | findstr "5000\|8000"
foreach ($line in $processes) {
    if ($line -match '\s(\d+)$') {
        $pid = $matches[1]
        Write-Host "  Stopping process $pid..." -ForegroundColor Gray
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    }
}
Start-Sleep -Seconds 1

Write-Host ""
Write-Host "┌─────────────────────────────────────────────────────────────┐" -ForegroundColor Cyan
Write-Host "│ STARTING BACKEND ON PORT 5000                             │" -ForegroundColor Cyan
Write-Host "└─────────────────────────────────────────────────────────────┘" -ForegroundColor Cyan
Write-Host ""

# Start backend in new window
$backendCmd = {
    cd $using:backendDir
    & $using:pythonExe app.py
}
$backendJob = Start-Job -ScriptBlock $backendCmd -Name "NitA_Backend"
Write-Host "Backend started (Job ID: $($backendJob.Id))" -ForegroundColor Green

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "┌─────────────────────────────────────────────────────────────┐" -ForegroundColor Cyan
Write-Host "│ STARTING FRONTEND ON PORT 8000                            │" -ForegroundColor Cyan
Write-Host "└─────────────────────────────────────────────────────────────┘" -ForegroundColor Cyan
Write-Host ""

# Start frontend in new window
$frontendCmd = {
    cd $using:projectRoot
    & $using:pythonExe -m http.server 8000 --directory frontend
}
$frontendJob = Start-Job -ScriptBlock $frontendCmd -Name "NitA_Frontend"
Write-Host "Frontend started (Job ID: $($frontendJob.Id))" -ForegroundColor Green

Start-Sleep -Seconds 2

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                    ✅ SYSTEMS STARTING                        ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

Write-Host "WAITING FOR SERVICES TO BE READY..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Test connections
Write-Host ""
Write-Host "═══ Connection Tests ═══" -ForegroundColor Cyan
Write-Host ""

# Test backend
Write-Host "Testing Backend (http://localhost:5000/api/health)..." -ForegroundColor Gray
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5000/api/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "✅ Backend: ONLINE (Status $($response.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Backend: Not responding yet (might take a moment to start)" -ForegroundColor Yellow
}

# Test frontend
Write-Host "Testing Frontend (http://localhost:8000/index.html)..." -ForegroundColor Gray
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/index.html" -UseBasicParsing -TimeoutSec 5
    Write-Host "✅ Frontend: ONLINE (Status $($response.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Frontend: Not responding yet (might take a moment to start)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "🚀 SYSTEM READY!" -ForegroundColor Green
Write-Host ""
Write-Host "FRONTEND URL: http://localhost:8000" -ForegroundColor Green
Write-Host "BACKEND URL:  http://localhost:5000/api" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "1. Open your browser"
Write-Host "2. Navigate to: http://localhost:8000"
Write-Host "3. Start using the application"
Write-Host ""
Write-Host "To stop the servers:" -ForegroundColor Yellow
Write-Host "  Stop-Job -Name NitA_Backend" -ForegroundColor Gray
Write-Host "  Stop-Job -Name NitA_Frontend" -ForegroundColor Gray
Write-Host ""

# Keep script running and show output
Write-Host "Monitoring services... (Press Ctrl+C to stop)" -ForegroundColor Cyan
Write-Host ""

try {
    # Show live backend output
    Get-Job -Name "NitA_Backend" | Receive-Job -Wait
} catch {
    Write-Host "Services stopped" -ForegroundColor Yellow
}
