# Requirements Files Guide

## 📋 Overview

This project has multiple requirements files for different purposes. All files are now **synchronized** with the main `requirements.txt` to avoid conflicts.

## 📁 Requirements Files

### 1. `requirements.txt` (MAIN FILE)
- **Purpose**: Primary requirements file for all deployments
- **Used by**: 
  - Local development (`pip install -r requirements.txt`)
  - Docker builds (`COPY requirements.txt .`)
  - DigitalOcean App Platform (via `PIP_REQUIREMENTS` in `app.yaml`)
- **Status**: ✅ **ACTIVE** - This is the source of truth

### 2. `requirements_sharekhan.txt`
- **Purpose**: ShareKhan integration specific requirements
- **Used by**: ShareKhan standalone scripts and integration tests
- **Status**: ✅ **SYNCED** - Now matches main requirements.txt

### 3. `requirements_python311.txt`
- **Purpose**: Python 3.11 specific compatibility
- **Used by**: Python 3.11 environments
- **Status**: ✅ **SYNCED** - Now matches main requirements.txt

### 4. `requirements_python313_compatible.txt`
- **Purpose**: Python 3.13 compatibility workaround
- **Used by**: Python 3.13 environments
- **Status**: ✅ **SYNCED** - Now matches main requirements.txt

## 🔄 Synchronization

All requirements files are automatically synced with `requirements.txt` using the `sync_requirements.py` script:

```bash
python sync_requirements.py
```

## 🚀 Deployment

### Local Development
```bash
pip install -r requirements.txt
```

### DigitalOcean App Platform
- Uses `PIP_REQUIREMENTS` environment variable in `app.yaml`
- This variable contains the same dependencies as `requirements.txt`
- Updated automatically when `requirements.txt` changes

### Docker
```dockerfile
COPY requirements.txt .
RUN pip install -r requirements.txt
```

## 📦 Key Dependencies

### Core Framework
- `fastapi>=0.104.1` - Web framework
- `uvicorn[standard]>=0.24.0` - ASGI server
- `pydantic>=2.11.7` - Data validation

### Database & Caching
- `redis>=5.0.1` - Redis client
- `psycopg2-binary>=2.9.9` - PostgreSQL adapter
- `sqlalchemy>=2.0.23` - ORM

### HTTP & WebSocket
- `httpx>=0.25.2` - HTTP client (CRITICAL for API calls)
- `aiohttp>=3.9.1` - Async HTTP client
- `websockets>=12.0` - WebSocket support

### Trading & Data
- `sharekhan>=7.0.0` - ShareKhan SDK
- `sharekhantconnect>=4.2.0` - ShareKhan API
- `pandas>=2.1.4` - Data analysis
- `numpy>=1.24.3` - Numerical computing

### Security & Auth
- `PyJWT>=2.3.0` - JWT tokens
- `bcrypt>=4.0.1` - Password hashing
- `cryptography>=41.0.7` - Encryption

## ⚠️ Important Notes

1. **Always use `requirements.txt`** as the primary source
2. **Run `sync_requirements.py`** after updating main requirements
3. **Check `PIP_REQUIREMENTS`** in `app.yaml` matches main requirements
4. **`httpx>=0.25.2`** is critical for API functionality

## 🔧 Troubleshooting

### Missing Dependencies
If you get import errors, ensure:
1. All requirements files are synced
2. `PIP_REQUIREMENTS` in `app.yaml` is up to date
3. DigitalOcean deployment uses the correct requirements

### Version Conflicts
If you get version conflicts:
1. Update `requirements.txt` with compatible versions
2. Run `sync_requirements.py` to update all files
3. Update `PIP_REQUIREMENTS` in `app.yaml`

### Deployment Issues
If DigitalOcean deployment fails:
1. Check `PIP_REQUIREMENTS` syntax in `app.yaml`
2. Verify all dependencies are compatible
3. Check DigitalOcean build logs for specific errors 