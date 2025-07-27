#!/bin/bash

# Exit on any error
set -e

echo "Starting frontend build process..."

# Install dependencies
echo "Installing dependencies..."
npm ci --production=false

# Build the application
echo "Building the application..."
npm run build

# Verify the build output
echo "Verifying build output..."
if [ ! -d "dist" ]; then
    echo "Error: dist directory not found after build"
    exit 1
fi

echo "Build completed successfully!"
ls -la dist/ 