// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://quantumcrypto-l43mb.ondigitalocean.app';
const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'wss://quantumcrypto-l43mb.ondigitalocean.app/ws';

// UNIFIED USER CONFIGURATION - Standardizes all user identifiers
export const USER_CONFIG = {
    // Primary user identifier (now unified with Zerodha user)
    PRIMARY_USER_ID: 'QSW899',

    // Zerodha broker user ID (same as primary for consistency)
    ZERODHA_USER_ID: 'QSW899',

    // Display names for different contexts
    DISPLAY_NAMES: {
        MASTER: 'Master Trader (QSW899)',
        PAPER: 'Live Trading Account',
        ZERODHA: 'Zerodha Account (QSW899)'
    },

    // User type mappings (unified to use real Zerodha user)
    USER_TYPES: {
        MASTER: 'QSW899',
        PAPER: 'QSW899',
        ZERODHA: 'QSW899',
        DATABASE: 'QSW899'
    },

    // API parameter mappings
    API_PARAMS: {
        DATABASE_QUERIES: 'user_id', // For database endpoints
        ZERODHA_OPERATIONS: 'user_id', // For Zerodha endpoints  
        USER_MANAGEMENT: 'user_id', // For user management
        DISPLAY_CONTEXT: 'username' // For display purposes
    }
};

// Helper functions for user identification
export const getUserIdentifier = (context = 'default') => {
    switch (context) {
        case 'database':
        case 'trading':
        case 'performance':
            return USER_CONFIG.PRIMARY_USER_ID;
        case 'zerodha':
        case 'broker':
            return USER_CONFIG.ZERODHA_USER_ID;
        case 'display':
            return USER_CONFIG.DISPLAY_NAMES.MASTER;
        default:
            return USER_CONFIG.PRIMARY_USER_ID;
    }
};

export const getUserDisplayName = (userId) => {
    if (userId === USER_CONFIG.PRIMARY_USER_ID || userId === 'MASTER_USER_001') {
        return USER_CONFIG.DISPLAY_NAMES.MASTER;
    }
    if (userId === USER_CONFIG.ZERODHA_USER_ID) {
        return USER_CONFIG.DISPLAY_NAMES.ZERODHA;
    }
    return userId;
};

// Ensure API_BASE_URL doesn't end with a slash
const normalizedApiUrl = API_BASE_URL.endsWith('/') ? API_BASE_URL.slice(0, -1) : API_BASE_URL;

// Add error handling wrapper
const createEndpoint = (path, requiresTrailingSlash = false) => {
    // Ensure path starts with a slash
    let normalizedPath = path.startsWith('/') ? path : `/${path}`;

    // Add trailing slash if required
    if (requiresTrailingSlash && !normalizedPath.endsWith('/')) {
        normalizedPath += '/';
    }

    const fullUrl = `${normalizedApiUrl}${normalizedPath}`;

    return {
        url: fullUrl,
        fallback: {
            success: false,
            error: 'Service temporarily unavailable',
            data: null
        }
    };
};

export const API_ENDPOINTS = {
    // Auth endpoints - UNIFIED: All use consistent paths
    LOGIN: createEndpoint('/api/auth/login'),
    REGISTER: createEndpoint('/api/auth/register'),
    LOGOUT: createEndpoint('/api/auth/logout'),
    REFRESH_TOKEN: createEndpoint('/api/auth/refresh-token'),
    USER_PROFILE: createEndpoint('/api/auth/me'),

    // UNIFIED User Management endpoints - All use PRIMARY_USER_ID
    USERS: createEndpoint('/api/v1/users/performance', true),
    USER_PERFORMANCE: createEndpoint('/api/v1/users/performance'),
    USER_CURRENT: createEndpoint('/api/v1/users/current'),
    USER_ANALYTICS: createEndpoint('/api/v1/user-analytics'),

    // UNIFIED Broker user management - Uses consistent user identification
    BROKER_USERS: createEndpoint('/api/v1/control/users/broker'),

    // UNIFIED Trading endpoints - All use PRIMARY_USER_ID for consistency
    TRADES: createEndpoint('/api/v1/trades', true),
    POSITIONS: createEndpoint('/api/v1/positions', true),
    ORDERS: createEndpoint('/api/v1/orders', true),
    // Added missing endpoints for complete coverage
    RISK_METRICS: createEndpoint('/api/v1/risk/metrics'),
    STRATEGIES: createEndpoint('/api/v1/strategies'),
    AUTONOMOUS: createEndpoint('/api/v1/autonomous'),

    // Trading control endpoints
    TRADING_CONTROL: createEndpoint('/api/v1/control/trading/control'),
    TRADING_STATUS: createEndpoint('/api/v1/control/trading/status'),

    // Market data endpoints
    MARKET_INDICES: createEndpoint('/api/market/indices'),
    MARKET_STATUS: createEndpoint('/api/market/market-status'),
    MARKET_DATA: createEndpoint('/api/v1/market-data/NIFTY'),
    SYMBOLS: createEndpoint('/api/market/symbols'),

    // Strategy endpoints
    STRATEGIES: createEndpoint('/api/v1/autonomous/strategies'),
    STRATEGY_PERFORMANCE: createEndpoint('/api/v1/strategies/performance'),

    // Dashboard endpoints
    DASHBOARD_SUMMARY: createEndpoint('/api/v1/dashboard/summary'),
    DAILY_PNL: createEndpoint('/api/v1/monitoring/daily-pnl'),
    RECOMMENDATIONS: createEndpoint('/api/v1/elite', true),
    ELITE_RECOMMENDATIONS: createEndpoint('/api/v1/elite', true),
    DASHBOARD_DATA: createEndpoint('/api/v1/dashboard/data'),

    // Broker endpoints
    BROKER_CONNECT: createEndpoint('/api/v1/broker/connect'),
    BROKER_DISCONNECT: createEndpoint('/api/v1/broker/disconnect'),
    BROKER_STATUS: createEndpoint('/api/v1/broker/status'),

    // System endpoints
    SYSTEM_STATUS: createEndpoint('/api/v1/system/status'),
    SYSTEM_LOGS: createEndpoint('/api/v1/system/logs'),
    SYSTEM_METRICS: createEndpoint('/api/v1/system/metrics'),

    // Risk management endpoints
    RISK_METRICS: createEndpoint('/api/v1/risk/metrics'),
    RISK_LIMITS: createEndpoint('/api/v1/risk/limits'),
    RISK_ALERTS: createEndpoint('/api/v1/risk/alerts'),

    // Autonomous trading endpoints
    AUTONOMOUS_STATUS: createEndpoint('/api/v1/autonomous/status'),
    AUTONOMOUS_START: createEndpoint('/api/v1/autonomous/start'),
    AUTONOMOUS_STOP: createEndpoint('/api/v1/autonomous/stop'),
    AUTONOMOUS_CONTROL: createEndpoint('/api/v1/autonomous/control'),
    AUTONOMOUS_DATA: createEndpoint('/api/v1/autonomous/status'),

    // WebSocket endpoints
    WS_ENDPOINT: `${WS_BASE_URL}/ws`,
    WS_MARKET_DATA: `${WS_BASE_URL}/ws`,
    WS_ORDERS: `${WS_BASE_URL}/ws`,
    WS_POSITIONS: `${WS_BASE_URL}/ws`,

    // Additional endpoints
    TICK_DATA: createEndpoint('/api/v1/tick-data'),
    ORDER_BOOK: createEndpoint('/api/v1/order-book'),
    ACCOUNT: createEndpoint('/api/v1/account'),
    HEALTH: createEndpoint('/health'),
    HEALTH_READY_JSON: createEndpoint('/health/ready/json'),
    METRICS: createEndpoint('/metrics'),
    CONFIG: createEndpoint('/config'),

    // UNIFIED Zerodha Authentication endpoints - Use consistent user identification
    ZERODHA_AUTH_URL: createEndpoint('/auth/zerodha/auth-url'),
    ZERODHA_AUTH_STATUS: createEndpoint('/auth/zerodha/status'),
    ZERODHA_SUBMIT_TOKEN: createEndpoint('/auth/zerodha/submit-token'),
    ZERODHA_TEST_CONNECTION: createEndpoint('/auth/zerodha/test-connection'),
    ZERODHA_LOGOUT: createEndpoint('/auth/zerodha/logout'),
    ZERODHA_LOGIN: createEndpoint('/api/zerodha/login'),

    // Search endpoints
    SEARCH_SYMBOLS: createEndpoint('/api/v1/search/symbols'),
    SEARCH_TRADES: createEndpoint('/api/v1/search/trades'),
    SEARCH_STRATEGIES: createEndpoint('/api/v1/search/strategies'),
    SEARCH_USERS: createEndpoint('/api/v1/search/users'),
    SEARCH_RECOMMENDATIONS: createEndpoint('/api/v1/search/recommendations'),
    SEARCH_GLOBAL: createEndpoint('/api/v1/search/global'),
    SEARCH_AUTOCOMPLETE: createEndpoint('/api/v1/search/autocomplete'),
};

// UNIFIED API Helper functions
export const buildUserEndpoint = (baseEndpoint, context = 'database') => {
    const userId = getUserIdentifier(context);
    const paramName = USER_CONFIG.API_PARAMS.DATABASE_QUERIES;
    return `${baseEndpoint}?${paramName}=${userId}`;
};

export const buildZerodhaEndpoint = (baseEndpoint) => {
    const userId = getUserIdentifier('zerodha');
    return `${baseEndpoint}?user_id=${userId}`;
};