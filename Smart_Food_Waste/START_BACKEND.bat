@echo off
echo ============================================
echo Starting Backend Server
echo ============================================
echo.

cd backend

echo Checking virtual environment...
if not exist "..\venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please create it first: python -m venv venv
    pause
    exit /b 1
)

echo Activating virtual environment...
call ..\venv\Scripts\activate.bat

echo.
echo Checking dependencies...
python -c "import flask" 2>nul
if errorlevel 1 (
    echo ERROR: Flask not installed!
    echo Installing dependencies...
    pip install -r requirements.txt
)

echo.
echo Starting server...
echo.
python app.py

pause


