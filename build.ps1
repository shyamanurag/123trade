# Build script for Digital Ocean deployment (PowerShell)

Write-Host "Building frontend..."
Set-Location src/frontend
npm install
npm run build

Write-Host "Copying frontend assets to root dist directory..."
Set-Location ../..
New-Item -ItemType Directory -Force -Path dist
Copy-Item -Path "src/frontend/dist/*" -Destination "dist/" -Recurse -Force

Write-Host "Build complete! Frontend assets are now in /dist"
