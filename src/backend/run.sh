#!/bin/bash

# Trap Ctrl+C and kill all child processes
trap 'echo "Shutting down..."; kill $(jobs -p); exit' INT TERM

# Check if port 8000 is already in use
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "Port 8000 is already in use. Killing existing process..."
    lsof -ti:8000 | xargs kill -9
    sleep 1
fi

# Run the FastAPI application in development mode
# Using exec to replace the shell process with uvicorn
exec uvicorn src.app:app --reload --host 0.0.0.0 --port 8000 