#!/bin/bash

# Dementia Aid Services Startup Script
# This script starts both the Python face recognition service and the MCP server

echo "🚀 Starting Dementia Aid Services..."
echo "=================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed or not in PATH"
    exit 1
fi

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed or not in PATH"
    exit 1
fi

# Check for environment variables
echo "🔍 Checking environment configuration..."

# Check MCP server environment
if [ -f "mcp-server/.env" ]; then
    echo "   ✅ MCP server .env found"
else
    echo "   ⚠️  MCP server .env not found - using defaults"
fi

# Check Python service environment
if [ -f "python-face-service/.env" ]; then
    echo "   ✅ Python service .env found"
else
    echo "   ⚠️  Python service .env not found - Supabase features will be limited"
fi

# Check Python dependencies
echo "🐍 Checking Python dependencies..."
cd python-face-service
if python3 -c "import supabase, fastapi, cv2, numpy, PIL" 2>/dev/null; then
    echo "   ✅ All Python dependencies available"
else
    echo "   ⚠️  Some Python dependencies missing - run: pip install -r requirements.txt"
fi
cd ..

echo ""

# Function to cleanup background processes
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    if [ ! -z "$PYTHON_PID" ]; then
        kill $PYTHON_PID 2>/dev/null
        echo "   ✅ Python service stopped"
    fi
    if [ ! -z "$MCP_PID" ]; then
        kill $MCP_PID 2>/dev/null
        echo "   ✅ MCP server stopped"
    fi
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start Python face recognition service
echo "🐍 Starting Python face recognition service..."
cd python-face-service
python3 face_service.py &
PYTHON_PID=$!
cd ..

# Wait a moment for Python service to start
echo "⏳ Waiting for Python service to initialize..."
sleep 3

# Check if Python service is running
if ! kill -0 $PYTHON_PID 2>/dev/null; then
    echo "❌ Failed to start Python service"
    exit 1
fi

# Test Python service health
echo "🔍 Testing Python service health..."
if curl -s http://localhost:8001/health > /dev/null; then
    echo "   ✅ Python service is healthy"
else
    echo "   ⚠️  Python service may not be ready yet"
fi

# Start MCP server
echo "🔧 Starting MCP server..."
cd mcp-server
npm run dev &
MCP_PID=$!
cd ..

# Wait a moment for MCP server to start
echo "⏳ Waiting for MCP server to initialize..."
sleep 2

# Check if MCP server is running
if ! kill -0 $MCP_PID 2>/dev/null; then
    echo "❌ Failed to start MCP server"
    cleanup
    exit 1
fi

echo ""
echo "✅ Both services are running!"
echo "   🐍 Python face service: http://localhost:8001"
echo "   🔧 MCP server: Running in development mode"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for user interrupt
wait
