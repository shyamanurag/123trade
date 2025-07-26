# Deployment URLs Guide

## The URL Problem

When creating a fresh DigitalOcean app, you won't know the final URL until after the first deployment. The URLs in the codebase (`trade123-l3zp7.ondigitalocean.app`) are from the current deployment.

## Solution Steps

### 1. Initial Deployment with Placeholder URLs

For the first deployment, use placeholder URLs in `app.yaml`:

```yaml
- key: VITE_API_URL
  value: https://YOUR-APP-NAME.ondigitalocean.app/api
- key: VITE_WS_URL
  value: wss://YOUR-APP-NAME.ondigitalocean.app/ws
- key: APP_URL
  value: https://YOUR-APP-NAME.ondigitalocean.app
- key: FRONTEND_URL
  value: https://YOUR-APP-NAME.ondigitalocean.app
- key: CORS_ORIGINS
  value: '["https://YOUR-APP-NAME.ondigitalocean.app", "http://localhost:3000", "http://localhost:5173"]'
```

### 2. After First Deployment

Once DigitalOcean assigns your app URL (e.g., `algoauto-xyz123.ondigitalocean.app`):

1. Update all URLs in `app.yaml` with the actual URL
2. Commit and push to trigger a rebuild
3. The app will then work with the correct URLs

### 3. Testing Scripts

Use the updated test scripts that accept URLs as parameters:

```bash
# Test locally
python test_deployment_v2.py http://localhost:8000

# Test deployed app (after getting URL)
python test_deployment_v2.py https://your-actual-app.ondigitalocean.app
```

### 4. Environment-Based Configuration

For local development, use `.env` files:

```env
APP_URL=http://localhost:8000
VITE_API_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws
```

### 5. Files That Need URL Updates

After getting your actual DigitalOcean URL, update these files:

1. **app.yaml** - All environment variables with URLs
2. **src/frontend/vite.config.js** - Default fallback URLs (optional)
3. **src/frontend/api/config.js** - Default fallback URLs (optional)
4. **src/frontend/hooks/useWebSocket.js** - Default fallback URLs (optional)

### 6. Alternative: Use DigitalOcean App Platform Environment Variables

Instead of hardcoding URLs, you can:

1. Deploy with placeholder values
2. After deployment, update environment variables in DigitalOcean App Platform UI
3. Trigger a redeploy

This way, you don't need to change code after getting the URL.

## Quick Start Commands

```bash
# 1. Initial deployment (URLs will be wrong but app structure will deploy)
git push origin main

# 2. After getting actual URL from DigitalOcean, update app.yaml
# Replace YOUR-APP-NAME with actual URL

# 3. Test the deployed app
python test_deployment_v2.py https://your-actual-app.ondigitalocean.app

# 4. If tests pass, you're done!
``` 