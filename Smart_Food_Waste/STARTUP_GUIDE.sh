#!/bin/bash
# NitA - Start Both Backend and Frontend Servers
# This script starts the complete system

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║      NitA AI-Powered Smart Food Waste Management System       ║"
echo "║                   Complete Startup Guide                      ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}IMPORTANT: You need to open TWO separate terminal windows${NC}"
echo ""
echo -e "${BLUE}═══ TERMINAL 1 (Backend) ═══${NC}"
echo "1. Open a new PowerShell window"
echo "2. Navigate to the project folder:"
echo "   cd 'f:\Code Playground\NitA\updated1\NitA\backend'"
echo "3. Run the Flask backend:"
echo "   F:\Code Playground\NitA\updated1\NitA\.venv\Scripts\python.exe app.py"
echo ""
echo "   The backend will start on: http://localhost:5000"
echo "   Keep this window open and running"
echo ""

echo -e "${BLUE}═══ TERMINAL 2 (Frontend) ═══${NC}"
echo "1. Open another new PowerShell window"
echo "2. Navigate to the project folder:"
echo "   cd 'f:\Code Playground\NitA\updated1\NitA'"
echo "3. Start the frontend server:"
echo "   F:\Code Playground\NitA\updated1\NitA\.venv\Scripts\python.exe -m http.server 8000 --directory frontend"
echo ""
echo "   The frontend will be available at: http://localhost:8000"
echo "   Keep this window open and running"
echo ""

echo -e "${GREEN}═══ Once Both Are Running ═══${NC}"
echo "1. Open your browser"
echo "2. Go to: http://localhost:8000"
echo "3. The frontend should connect to the backend at http://localhost:5000"
echo ""

echo "✅ Backend running on:  http://localhost:5000/api"
echo "✅ Frontend running on: http://localhost:8000"
echo "✅ CORS enabled for both localhost ports"
echo ""
