#!/bin/bash

# Automated Shorts Generator - Quick Start Script

echo "============================================================"
echo "🎬 Automated Shorts Generator"
echo "============================================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found!"
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
    echo ""
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
    echo "✅ Dependencies installed"
    echo ""
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo "📝 Creating .env from template..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env file with your API keys:"
    echo "   - RUNPOD_API_KEY"
    echo "   - RUNPOD_ENDPOINT"
    echo "   - OPENROUTER_API_KEY"
    echo ""
    echo "Run this script again after configuring .env"
    exit 1
fi

# Check FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  FFmpeg not found!"
    echo "Please install FFmpeg:"
    echo "  brew install ffmpeg"
    exit 1
fi

echo "✅ All checks passed!"
echo ""
echo "🚀 Starting Automated Shorts Generator..."
echo "🌐 Open http://localhost:8000 in your browser"
echo ""
echo "Press Ctrl+C to stop the server"
echo "============================================================"
echo ""

# Start the application
python main.py
