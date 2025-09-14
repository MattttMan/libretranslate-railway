#!/bin/bash

echo "🚀 LibreTranslate Lite Test Script"
echo "=================================="

# Check if we're in the right directory
if [ ! -f "translate_api.py" ]; then
    echo "❌ Error: translate_api.py not found. Make sure you're in the right directory."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install fastapi uvicorn requests
else
    echo "📦 Using existing virtual environment..."
    source venv/bin/activate
fi

# Start the API in the background
echo "🔄 Starting LibreTranslate Lite API..."
python translate_api.py &
API_PID=$!

# Wait for API to start
echo "⏳ Waiting for API to start..."
sleep 3

# Test the API
echo "🧪 Testing the API..."
python test_api.py

# Stop the API
echo "🛑 Stopping API..."
kill $API_PID 2>/dev/null

echo "✅ Test completed!"
