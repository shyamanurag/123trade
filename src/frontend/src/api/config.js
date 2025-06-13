// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://algoauto-ua2iq.ondigitalocean.app';

export const API_ENDPOINTS = {
    // Auth endpoints
    LOGIN: `${API_BASE_URL}/api/auth/login`,
    REGISTER: `${API_BASE_URL}/api/auth/register`,
    LOGOUT: `${API_BASE_URL}/api/auth/logout`,
    REFRESH_TOKEN: `${API_BASE_URL}/api/auth/refresh-token`,

    // User endpoints
    USERS: `${API_BASE_URL}/api/users`,
    USER_PROFILE: `${API_BASE_URL}/api/users/profile`,

    // Trading endpoints
    TRADES: `${API_BASE_URL}/api/trades`,
    POSITIONS: `${API_BASE_URL}/api/positions`,
    ORDERS: `${API_BASE_URL}/api/orders`,

    // Market data endpoints
    MARKET_DATA: `${API_BASE_URL}/api/market-data`,
    SYMBOLS: `${API_BASE_URL}/api/symbols`,

    // Strategy endpoints
    STRATEGIES: `${API_BASE_URL}/api/strategies`,
    STRATEGY_PERFORMANCE: `${API_BASE_URL}/api/strategies/performance`,

    // Broker endpoints
    BROKER_CONNECT: `${API_BASE_URL}/api/broker/connect`,
    BROKER_DISCONNECT: `${API_BASE_URL}/api/broker/disconnect`,
    BROKER_STATUS: `${API_BASE_URL}/api/broker/status`,

    // System endpoints
    SYSTEM_STATUS: `${API_BASE_URL}/api/system/status`,
    SYSTEM_LOGS: `${API_BASE_URL}/api/system/logs`,
    SYSTEM_METRICS: `${API_BASE_URL}/api/system/metrics`
};

export default API_ENDPOINTS; 