@echo off
REM Start Frontend Server on port 8000
REM This batch file serves the frontend HTML/CSS/JS files

cd /d "%~dp0"

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║         NitA Frontend Server - Starting on Port 8000           ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo [INFO] Starting Python HTTP server...
echo [INFO] Frontend will be available at: http://localhost:8000
echo [INFO] Make sure Flask backend is running on http://localhost:5000
echo.

python -m http.server 8000 --directory frontend

pause
