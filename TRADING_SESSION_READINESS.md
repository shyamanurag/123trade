# Trading Session Readiness Checklist

## Current Status (81% API Success Rate)
- ✅ All critical trading endpoints are working (positions, orders, trades)
- ✅ User management and authentication working
- ✅ Market data endpoints operational
- ✅ Monitoring endpoints functional
- ✅ Default ShareKhan user added successfully

## Remaining Issues to Fix

### 1. WebSocket Connection (Critical for Real-time Updates)
**Issue**: WebSocket returning 403 Forbidden
**Solution**: Update Digital Ocean app spec with proper WebSocket ingress rules
```yaml
ingress:
  rules:
  - component:
      name: api
      rewrite: /ws
    match:
      path:
        prefix: /ws
```

### 2. Daily P&L Endpoint (Medium Priority)
**Issue**: Timing out with 504 error
**Solution**: Optimize database query or add caching
- Consider adding Redis caching for P&L calculations
- Limit query time range to last 30 days by default

### 3. Authentication Status Codes (Low Priority)
**Issue**: Returning 403 instead of 401 for unauthenticated requests
**Solution**: Update auth middleware to return proper status codes

## Pre-Trading Checklist

### 1. ShareKhan Authentication
- [ ] Run daily authentication at `/sharekhan` endpoint
- [ ] Verify access token is valid
- [ ] Check if paper trading mode is enabled

### 2. System Health Checks
- [ ] Run `python scripts/test_production_api.py` to verify all endpoints
- [ ] Check database connectivity
- [ ] Verify Redis cache is operational
- [ ] Monitor system resources (CPU, Memory)

### 3. Trading Configuration
- [ ] Verify trading hours are configured correctly
- [ ] Check risk management limits
- [ ] Confirm capital allocation settings
- [ ] Review active strategies

### 4. Manual Digital Ocean Updates Required
1. **Update App Spec for WebSocket**:
   - Go to Digital Ocean App Platform
   - Edit app spec
   - Add WebSocket ingress rule
   - Deploy changes

2. **Monitor Deployment**:
   - Watch for deployment completion
   - Check build logs for errors
   - Verify new endpoints are accessible

## Quick Start Commands

```bash
# Test API endpoints
python scripts/test_production_api.py

# Add ShareKhan user (if needed)
python scripts/add_default_sharekhan_user.py

# Monitor logs
doctl apps logs <app-id> --follow

# Check deployment status
doctl apps list
```

## Emergency Contacts
- Digital Ocean Support: https://www.digitalocean.com/support/
- ShareKhan Support: support@sharekhan.in
- ShareKhan Support: https://support.sharekhan.com/

## Trading Session Timeline
1. **8:00 AM**: Run system health checks
2. **8:30 AM**: Execute ShareKhan daily authentication
3. **8:45 AM**: Verify all systems operational
4. **9:00 AM**: Enable automated trading
5. **9:15 AM**: Market opens - monitor initial trades
6. **Throughout Day**: Monitor system performance
7. **3:30 PM**: Market closes - generate daily reports

## Success Metrics
- All API endpoints returning < 500ms response time
- WebSocket connections stable
- No authentication failures
- Zero system crashes
- Successful order execution rate > 95% 