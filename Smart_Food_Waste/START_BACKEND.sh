#!/bin/bash

echo "============================================"
echo "Starting Backend Server"
echo "============================================"
echo ""

cd backend

# Activate virtual environment
if [ -d "../venv" ]; then
    source ../venv/bin/activate
    echo "✓ Virtual environment activated"
else
    echo "ERROR: Virtual environment not found!"
    echo "Please create it first: python -m venv venv"
    exit 1
fi

# Check dependencies
python -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

echo ""
echo "Starting server..."
echo ""
python app.py


