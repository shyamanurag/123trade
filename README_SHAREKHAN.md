# ShareKhan Trading System

🚀 **Complete Architecture Replacement: ShareKhan + ShareKhan → ShareKhan Only**

This is a comprehensive trading system that completely replaces the old dual-provider architecture (ShareKhan for market data + ShareKhan for trading) with a unified ShareKhan API integration. The system now provides trading operations, real-time market data, and multi-user management all through ShareKhan's API.

## 🎯 Key Improvements

### Old Architecture Problems
- **Dual Provider Complexity**: ShareKhan for market data + ShareKhan for trading = 2 different APIs, 2 authentication systems, 2 failure points
- **Data Synchronization Issues**: Market data from ShareKhan, trading from ShareKhan - timing mismatches
- **Limited Multi-User Support**: Basic user management with single master account approach
- **Complex Deployment**: Multiple service dependencies and configurations

### New ShareKhan Architecture Benefits
- **Single API Integration**: All trading and market data through ShareKhan API
- **Unified Authentication**: One authentication system for everything
- **True Multi-User Support**: Individual user accounts with role-based permissions
- **Simplified Deployment**: Single integration point, fewer dependencies
- **Better Data Consistency**: Trading and market data from same source
- **Enhanced Security**: Centralized permission management

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    ShareKhan Trading System                 │
├─────────────────────────────────────────────────────────────┤
│  Multi-User Management (Role-based permissions)            │
├─────────────────────────────────────────────────────────────┤
│  ShareKhan Integration Layer                                │
│  ├── Trading Operations (Orders, Positions, Portfolio)     │
│  ├── Market Data (Real-time, Historical, WebSocket)        │
│  └── User Authentication & Management                       │
├─────────────────────────────────────────────────────────────┤
│  Core Trading Engine                                        │
│  ├── Risk Manager                                          │
│  ├── Order Manager                                         │
│  ├── Position Tracker                                      │
│  ├── Performance Analyzer                                  │
│  └── Strategy Engine (5 Built-in Strategies)             │
├─────────────────────────────────────────────────────────────┤
│  Data Layer                                                 │
│  ├── Redis (Caching & Sessions)                           │
│  ├── PostgreSQL/SQLite (Persistent Data)                  │
│  └── WebSocket (Real-time Data Broadcasting)              │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. Prerequisites

- **Python 3.8+**
- **Redis Server**
- **ShareKhan API Account** ([Get one here](https://newtrade.sharekhan.com/skweb/login/trading-api))
- **PostgreSQL** (recommended for production) or SQLite (for development)

### 2. Installation

```bash
# Clone the repository
git clone <repository-url>
cd trading-system-multi-account

# Install dependencies
pip install -r requirements.txt

# Copy configuration template
cp config/sharekhan.env.example .env

# Edit .env file with your ShareKhan credentials
nano .env
```

### 3. ShareKhan API Setup

1. Go to [ShareKhan Developer Portal](https://newtrade.sharekhan.com/skweb/login/trading-api)
2. Login with your ShareKhan credentials
3. Create a new app:
   - App Name: "ShareKhan Trading System"
   - Select Partner App option
4. Copy the API Key and Secret Key
5. Update your `.env` file:

```env
SHAREKHAN_API_KEY=your_api_key_here
SHAREKHAN_SECRET_KEY=your_secret_key_here
SHAREKHAN_MASTER_USER_ID=your_user_id
```

### 4. Database Setup

#### For Development (SQLite)
```bash
# Update .env file
DATABASE_URL=sqlite:///sharekhan_trading.db
```

#### For Production (PostgreSQL)
```bash
# Create database
createdb sharekhan_trading

# Update .env file
DATABASE_URL=postgresql://username:password@localhost:5432/sharekhan_trading
```

### 5. Redis Setup

```bash
# Install Redis
sudo apt-get install redis-server

# Start Redis
redis-server

# Test connection
redis-cli ping
```

### 6. Start the Application

```bash
# Development mode
python main_sharekhan.py

# Or using uvicorn directly
uvicorn main_sharekhan:app --host 0.0.0.0 --port 8000 --reload
```

### 7. Access the System

- **Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 👥 Multi-User System

### User Roles

1. **Admin**: Full system access, user management, system configuration
2. **Trader**: Full trading access, portfolio management, market data access
3. **Limited Trader**: Place orders only, view portfolio and trades
4. **Viewer**: Read-only access to portfolio and market data

### User Management

#### Create Users via API
```python
import requests

# Create a new trader
user_data = {
    "name": "John Trader",
    "email": "john@example.com",
    "password": "secure_password",
    "role": "trader",
    "trading_enabled": True,
    "max_position_size": 100000.0,
    "max_daily_loss": 10000.0,
    "max_orders_per_day": 100
}

response = requests.post(
    "http://localhost:8000/api/v1/sharekhan/users/create",
    json=user_data
)
```

#### User Authentication
```python
# Login
login_data = {
    "user_id": "john_trader",
    "password": "secure_password"
}

response = requests.post(
    "http://localhost:8000/api/v1/sharekhan/auth/login",
    json=login_data
)

access_token = response.json()["data"]["access_token"]

# Use token in subsequent requests
headers = {"Authorization": f"Bearer {access_token}"}
```

## 📊 Trading Operations

### Place Orders

```python
# Place a buy order
order_data = {
    "scrip_code": 2475,
    "trading_symbol": "RELIANCE",
    "exchange": "NSE",
    "transaction_type": "BUY",
    "quantity": 10,
    "price": 2500.0,
    "order_type": "LIMIT",
    "product_type": "DELIVERY"
}

response = requests.post(
    "http://localhost:8000/api/v1/sharekhan/orders/place",
    json=order_data,
    headers=headers
)
```

### Get Portfolio
```python
# Get positions
positions = requests.get(
    "http://localhost:8000/api/v1/sharekhan/positions",
    headers=headers
)

# Get holdings
holdings = requests.get(
    "http://localhost:8000/api/v1/sharekhan/holdings",
    headers=headers
)

# Get trades
trades = requests.get(
    "http://localhost:8000/api/v1/sharekhan/trades",
    headers=headers
)
```

## 📈 Market Data

### Subscribe to Real-time Data

```python
# Subscribe to symbols
symbols = ["RELIANCE", "TCS", "INFY", "HDFC"]
subscription_data = {
    "symbols": symbols,
    "user_id": "john_trader"
}

response = requests.post(
    "http://localhost:8000/api/v1/sharekhan/market-data/subscribe",
    json=subscription_data,
    headers=headers
)
```

### Get Live Data
```python
# Get live data for specific symbol
live_data = requests.get(
    "http://localhost:8000/api/v1/sharekhan/market-data/live?symbol=RELIANCE",
    headers=headers
)

# Get all subscribed data
all_data = requests.get(
    "http://localhost:8000/api/v1/sharekhan/market-data/live",
    headers=headers
)
```

### Historical Data
```python
# Get historical data
historical_data = requests.get(
    "http://localhost:8000/api/v1/sharekhan/market-data/historical/RELIANCE"
    "?interval=1min&from_date=2024-01-01&to_date=2024-01-02",
    headers=headers
)
```

## 🤖 Autonomous Trading

### Start Trading System
```python
# Start autonomous trading (admin only)
response = requests.post(
    "http://localhost:8000/api/v1/sharekhan/system/trading/start",
    headers=admin_headers
)
```

### Built-in Strategies

1. **Momentum Breakout**: Trades on price momentum breakouts
2. **Volume Profile Scalper**: High-frequency trading based on volume analysis
3. **Volatility Explosion**: Captures volatility expansion opportunities
4. **Confluence Amplifier**: Multi-indicator confluence trading
5. **Optimized Volume Scalper**: Enhanced volume-based scalping

### Strategy Configuration

Update strategy parameters in `.env`:
```env
MOMENTUM_STRATEGY_ENABLED=true
MOMENTUM_THRESHOLD=0.02
VOLUME_MULTIPLIER=2.0
VOLATILITY_WINDOW=20
```

## 🔧 System Administration

### System Status
```python
# Get detailed system status
status = requests.get("http://localhost:8000/api/v1/sharekhan/system/status")
print(status.json())
```

### Health Monitoring
```python
# Basic health check
health = requests.get("http://localhost:8000/health")

# Detailed health check
detailed_health = requests.get("http://localhost:8000/health/detailed")
```

### User Management (Admin)
```python
# List all users
users = requests.get(
    "http://localhost:8000/api/v1/sharekhan/admin/users",
    headers=admin_headers
)

# Get system statistics
stats = requests.get(
    "http://localhost:8000/api/v1/sharekhan/admin/system/stats",
    headers=admin_headers
)
```

## 📦 Deployment

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "main_sharekhan.py"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  trading-system:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - REDIS_URL=redis://redis:6379/0
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/sharekhan_trading
    depends_on:
      - redis
      - postgres
    volumes:
      - ./logs:/app/logs

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"

  postgres:
    image: postgres:13
    environment:
      POSTGRES_DB: sharekhan_trading
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Production Deployment

```bash
# Using Gunicorn for production
pip install gunicorn

# Start with multiple workers
gunicorn main_sharekhan:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

## 🔒 Security

### Environment Variables Security
- Never commit `.env` files to version control
- Use strong passwords and API keys
- Rotate credentials regularly
- Use environment-specific configurations

### API Security
- All endpoints require authentication
- Role-based access control
- Rate limiting implemented
- HTTPS enforced in production

### Trading Security
- Risk management at multiple levels
- Position size limits per user
- Daily loss limits
- Order frequency limits
- Emergency stop mechanisms

## 📊 Monitoring

### Built-in Monitoring
- Real-time system health checks
- Performance metrics tracking
- Connection status monitoring
- Trading activity analytics
- Risk violation alerts

### Metrics Endpoints
- `/health` - Basic health check
- `/health/detailed` - Comprehensive system status
- `/health/ready` - Kubernetes readiness probe
- `/health/live` - Kubernetes liveness probe

### Logging
- Structured logging to files and console
- Log rotation and retention
- Error tracking and alerting
- Audit trail for all trading activities

## 🚀 Migration from Old System

### Migration Checklist

- [ ] **API Credentials**: Set up ShareKhan API credentials
- [ ] **Database**: Migrate user data and trading history
- [ ] **Configuration**: Update environment variables
- [ ] **Users**: Recreate user accounts with new permissions
- [ ] **Strategies**: Reconfigure trading strategies
- [ ] **Testing**: Verify all functionality in paper trading mode
- [ ] **Deployment**: Deploy new system
- [ ] **Monitoring**: Set up monitoring and alerts

### Data Migration

The system includes migration utilities to transfer data from the old system:

```python
# Enable migration mode in .env
MIGRATION_MODE=true
MIGRATE_USER_DATA=true
MIGRATE_TRADING_HISTORY=true

# Run migration
python scripts/migrate_from_old_system.py
```

### Legacy Support

During migration, you can enable limited legacy support:

```env
LEGACY_SHAREKHAN_SUPPORT=false  # Set to true only during migration
LEGACY_SHAREKHAN_SUPPORT=false   # Set to true only during migration
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

- **Documentation**: [API Docs](http://localhost:8000/docs)
- **Issues**: Create GitHub issues for bugs and feature requests
- **Email**: support@sharekhan-trading.com

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This software is for educational and research purposes only. Trading in financial markets involves substantial risk of loss and is not suitable for all investors. Past performance is not indicative of future results. Please consult with a financial advisor before making investment decisions.

## 🔗 Links

- [ShareKhan API Documentation](https://newtrade.sharekhan.com/skweb/login/trading-api)
- [ShareKhan Developer Portal](https://newtrade.sharekhan.com/skweb/login/trading-api)
- [Redis Documentation](https://redis.io/documentation)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

---

**Built with ❤️ for automated trading excellence** 