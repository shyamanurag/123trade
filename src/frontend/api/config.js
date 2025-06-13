// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://algoauto-jd32t.ondigitalocean.app';

export const API_ENDPOINTS = {
    // Auth endpoints
    LOGIN: `${API_BASE_URL}/api/v1/auth/login`,
    REGISTER: `${API_BASE_URL}/api/v1/auth/register`,
    LOGOUT: `${API_BASE_URL}/api/v1/auth/logout`,
    REFRESH_TOKEN: `${API_BASE_URL}/api/v1/auth/refresh-token`,

    // User endpoints
    USERS: `${API_BASE_URL}/api/v1/users`,
    USER_PROFILE: `${API_BASE_URL}/api/v1/users/profile`,
    USER_PERFORMANCE: `${API_BASE_URL}/api/v1/users/performance`,

    // Trading endpoints
    TRADES: `${API_BASE_URL}/api/v1/trades`,
    POSITIONS: `${API_BASE_URL}/api/v1/positions`,
    ORDERS: `${API_BASE_URL}/api/v1/orders`,

    // Market data endpoints
    MARKET_DATA: `${API_BASE_URL}/api/v1/market-data`,
    SYMBOLS: `${API_BASE_URL}/api/v1/symbols`,

    // Strategy endpoints
    STRATEGIES: `${API_BASE_URL}/api/v1/strategies`,
    STRATEGY_PERFORMANCE: `${API_BASE_URL}/api/v1/strategies/performance`,

    // Dashboard endpoints
    DASHBOARD_SUMMARY: `${API_BASE_URL}/api/v1/dashboard/summary`,
    DAILY_PNL: `${API_BASE_URL}/api/v1/performance/daily-pnl`,
    RECOMMENDATIONS: `${API_BASE_URL}/api/v1/recommendations`,

    // Broker endpoints
    BROKER_CONNECT: `${API_BASE_URL}/api/v1/broker/connect`,
    BROKER_DISCONNECT: `${API_BASE_URL}/api/v1/broker/disconnect`,
    BROKER_STATUS: `${API_BASE_URL}/api/v1/broker/status`,

    // System endpoints
    SYSTEM_STATUS: `${API_BASE_URL}/api/v1/system/status`,
    SYSTEM_LOGS: `${API_BASE_URL}/api/v1/system/logs`,
    SYSTEM_METRICS: `${API_BASE_URL}/api/v1/system/metrics`
};

export default API_ENDPOINTS; 