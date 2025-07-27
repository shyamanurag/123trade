#!/bin/bash
# Build script for Digital Ocean deployment

echo "Building frontend..."
cd src/frontend
npm install
npm run build

echo "Copying frontend assets to root dist directory..."
cd ../..
mkdir -p dist
cp -r src/frontend/dist/* dist/

echo "Build complete! Frontend assets are now in /dist"
