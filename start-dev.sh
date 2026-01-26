#!/bin/bash
# Start all development servers for Alchemy
# Usage: ./start-dev.sh

cd "$(dirname "$0")"

echo "Starting Alchemy Development Environment..."
echo "==========================================="
echo ""
echo "Services:"
echo "  - Azure Functions API (port 7071)"
echo "  - Dev File Server"
echo "  - Next.js UI (port 3000)"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Use concurrently if available, otherwise fall back to background processes
if command -v npx &> /dev/null; then
    npx concurrently --kill-others --names "API,FILES,UI" --prefix-colors "blue,yellow,green" \
        "cd server/opinion/api-2 && source .venv/bin/activate && func start" \
        "cd server/opinion/api-2 && source .venv/bin/activate && python dev_file_server.py" \
        "cd ui && npm run dev"
else
    echo "Note: Install 'concurrently' for better output (npx concurrently)"
    echo ""

    # Trap to kill all background processes on exit
    trap 'kill $(jobs -p) 2>/dev/null' EXIT

    # Start services in background
    (cd server/opinion/api-2 && source .venv/bin/activate && func start) &
    (cd server/opinion/api-2 && source .venv/bin/activate && python dev_file_server.py) &
    (cd ui && npm run dev) &

    # Wait for all background processes
    wait
fi
