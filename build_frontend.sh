#!/bin/bash

# Build frontend for deployment
echo "Building frontend..."

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo "Node.js not found, skipping frontend build"
    exit 0
fi

# Check if npm is available
if ! command -v npm &> /dev/null; then
    echo "npm not found, skipping frontend build"
    exit 0
fi

# Navigate to frontend directory
cd src/frontend

# Install dependencies
echo "Installing frontend dependencies..."
npm ci

# Build the application
echo "Building frontend application..."
npm run build

# Check if build was successful
if [ -d "dist" ]; then
    echo "Frontend build successful!"
    ls -la dist/
else
    echo "Frontend build failed!"
    exit 1
fi 