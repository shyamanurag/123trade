# ShareKhan-Only Trading System Deployment

## Overview
This system has been completely converted to use ShareKhan APIs exclusively.
All ShareKhan and Sharekhan dependencies have been removed.

## Environment Variables Required

### ShareKhan Configuration
```
SHAREKHAN_API_KEY=your_sharekhan_api_key_here
SHAREKHAN_SECRET_KEY=your_sharekhan_secret_key_here
SHAREKHAN_CUSTOMER_ID=your_customer_id_here
SHAREKHAN_BASE_URL=https://api.sharekhan.com
SHAREKHAN_WS_URL=wss://ws.sharekhan.com
```

### Database Configuration (DigitalOcean PostgreSQL)
```
DATABASE_URL=postgresql://username:password@host:port/database?sslmode=require
```

### Redis Configuration (DigitalOcean Redis)
```
REDIS_URL=rediss://username:password@host:port
```

## Removed Components
- All ShareKhan clients and feeds
- All Sharekhan integrations
- All related authentication modules
- All legacy broker dependencies

## New ShareKhan Features
- Complete market data integration
- Real-time WebSocket feeds
- Order management system
- Position tracking
- Portfolio management
- Authentication handling

## Deployment Steps
1. Set environment variables in DigitalOcean App Platform
2. Deploy updated codebase
3. Verify ShareKhan API connectivity
4. Test trading functionality

## API Endpoints
All APIs now use ShareKhan backend:
- `/api/sharekhan/auth/*` - Authentication
- `/api/sharekhan/orders` - Order management
- `/api/sharekhan/positions` - Position tracking
- `/api/sharekhan/portfolio` - Portfolio data
- `/api/market/*` - Market data (ShareKhan powered)
