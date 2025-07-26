# Deployment Checklist for AlgoAuto Trading System

## DigitalOcean App Structure

DigitalOcean creates **TWO separate apps** from this repository:

1. **Backend API Service** (`api`):
   - Python/FastAPI application
   - Runs from root directory (`/`)
   - Entry point: `main.py`
   - Handles all `/api/*`, `/health`, `/docs` routes

2. **Frontend Static Site** (`frontend`):
   - React/Vite application
   - Built from `/src/frontend` directory
   - Outputs to `dist` directory
   - Serves all other routes (`/`)

The ingress rules in `app.yaml` route traffic between them.

## Issues Fixed

### 1. ✅ Health Check Endpoint
- **Problem**: Health check was looking for `/health/ready` but app only had `/health`
- **Fix**: Added `/health/ready` endpoint in `main.py`
- **Verification**: Both `/health` and `/health/ready` return proper JSON responses

### 2. ✅ Import Error Handling
- **Problem**: If imports fail, the entire app crashes
- **Fix**: Added try/catch for router imports with fallback error handling
- **Verification**: App starts even if some imports fail, with debug endpoint available

### 3. ✅ Environment File Loading
- **Problem**: App crashes if `config/production.env` doesn't exist
- **Fix**: Made dotenv loading optional with existence check
- **Verification**: App runs without the env file

### 4. ✅ Port Binding
- **Problem**: `$PORT` variable not properly handled in some shells
- **Fix**: Changed to `${PORT:-8000}` with default fallback
- **Added**: Logging flags for better debugging

### 5. ✅ Router Imports
- **Problem**: Potential circular imports or missing modules
- **Fix**: Verified all routers exist and export correctly:
  - `src.api.auth` exports `router_v1`
  - `src.api.market` exports `router`
  - `src.api.users` exports `router`

## Local Testing Results

```
✓ Health Check: 200
✓ Health Ready: 200
✓ Market Indices: 200
✓ Market Status: 200
✓ Users List: 200
✓ Current User: 200
✓ API Docs: 200
```

## Deployment Steps

1. **Commit Changes**:
   ```bash
   git add main.py app.yaml DEPLOYMENT_CHECKLIST.md test_local_app.py
   git commit -m "Fix deployment issues: health checks, imports, and port binding"
   git push origin main
   ```

2. **Monitor DigitalOcean Deployment**:
   - Check build logs for **BOTH** components (api and frontend)
   - Backend build logs will show Python/pip installation
   - Frontend build logs will show npm/vite build process
   - Both must succeed for the app to work

3. **Post-Deployment Verification**:
   ```bash
   python test_deployment_v2.py
   ```

## Build Issues to Watch For

### Backend (API) Component:
- Python version mismatch (should be 3.11.2)
- Missing dependencies in PIP_REQUIREMENTS
- Import errors in main.py
- Health check timeouts

### Frontend Component:
- Node version mismatch (should be 18.19.0)
- Missing npm packages
- Vite build errors
- Missing environment variables (VITE_*)

## Common Issues & Solutions

### If 530 Error Persists:
1. Check DigitalOcean build logs for Python errors
2. Verify all dependencies in `PIP_REQUIREMENTS` match `requirements.txt`
3. Check if database/Redis connections are failing

### If Import Errors Occur:
1. Check PYTHONPATH is set to `/app` in app.yaml
2. Verify all `__init__.py` files exist
3. Use debug endpoint: `https://trade123-l3zp7.ondigitalocean.app/debug/import-error`

### If Health Checks Fail:
1. Check logs with `--access-logfile -` and `--error-logfile -`
2. Verify the endpoint returns within 5 seconds (timeout_seconds: 5)
3. Check if database connections are blocking startup

## Next Steps After Successful Deployment

1. **Test All API Endpoints**:
   - Run `test_deployment_v2.py`
   - Check frontend can connect to API

2. **Monitor Logs**:
   - Watch for any runtime errors
   - Check WebSocket connections
   - Verify TrueData integration

3. **Database Migration** (if needed):
   - Run Alembic migrations
   - Verify tables are created

## Emergency Rollback

If deployment fails:
1. Revert to previous commit in DigitalOcean
2. Check what changed between working and broken versions
3. Test locally with exact same environment variables 