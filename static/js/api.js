// API Integration Layer for ShareKhan Trading Platform
class TradingAPI {
    constructor(baseURL = window.location.origin) {
        this.baseURL = baseURL;
        this.authToken = null;
        this.retryCount = 3;
        this.timeout = 10000; // 10 seconds
    }

    // Generic API request method
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const defaultOptions = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            timeout: this.timeout
        };

        // Add auth token if available
        if (this.authToken) {
            defaultOptions.headers['Authorization'] = `Bearer ${this.authToken}`;
        }

        const finalOptions = { ...defaultOptions, ...options };

        try {
            const response = await fetch(url, finalOptions);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            // Handle different content types
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            } else {
                return await response.text();
            }
        } catch (error) {
            console.error(`API request failed for ${endpoint}:`, error);
            throw error;
        }
    }

    // System Health and Status
    async getSystemStatus() {
        return await this.request('/api/system/status');
    }

    async getHealthCheck() {
        return await this.request('/health');
    }

    async getApiHealth() {
        return await this.request('/api/health');
    }

    async getDebugStatus() {
        return await this.request('/api/debug/status');
    }

    // ShareKhan API Integration
    async getSharekhanAuth() {
        return await this.request('/api/sharekhan/auth');
    }

    async refreshSharekhanToken() {
        return await this.request('/api/sharekhan/refresh-token', {
            method: 'POST'
        });
    }

    async getSharekhanProfile() {
        return await this.request('/api/sharekhan/profile');
    }

    // Market Data APIs
    async getMarketIndices() {
        try {
            // Try ShareKhan API first
            return await this.request('/api/sharekhan/indices');
        } catch (error) {
            // Fallback to mock data
            return {
                indices: [
                    { symbol: 'NIFTY50', ltp: 19850.45, change: 0.75 },
                    { symbol: 'BANKNIFTY', ltp: 44320.80, change: -0.32 },
                    { symbol: 'SENSEX', ltp: 66795.14, change: 0.45 }
                ],
                timestamp: new Date().toISOString()
            };
        }
    }

    async getQuote(symbol) {
        return await this.request(`/api/sharekhan/quote/${symbol}`);
    }

    async getMarketStatus() {
        return await this.request('/api/sharekhan/market-status');
    }

    // User Management APIs
    async getUsers() {
        return await this.request('/api/users');
    }

    async getUser(userId) {
        return await this.request(`/api/users/${userId}`);
    }

    async createUser(userData) {
        return await this.request('/api/users', {
            method: 'POST',
            body: JSON.stringify(userData)
        });
    }

    async updateUser(userId, userData) {
        return await this.request(`/api/users/${userId}`, {
            method: 'PUT',
            body: JSON.stringify(userData)
        });
    }

    async deleteUser(userId) {
        return await this.request(`/api/users/${userId}`, {
            method: 'DELETE'
        });
    }

    // Trading APIs
    async getPortfolio(userId = null) {
        const endpoint = userId ? `/api/portfolio/${userId}` : '/api/portfolio';
        return await this.request(endpoint);
    }

    async getPositions(userId = null) {
        const endpoint = userId ? `/api/positions/${userId}` : '/api/positions';
        return await this.request(endpoint);
    }

    async getOrders(userId = null) {
        const endpoint = userId ? `/api/orders/${userId}` : '/api/orders';
        return await this.request(endpoint);
    }

    async getTrades(userId = null, startDate = null, endDate = null) {
        let endpoint = userId ? `/api/trades/${userId}` : '/api/trades';

        const params = new URLSearchParams();
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);

        if (params.toString()) {
            endpoint += `?${params.toString()}`;
        }

        return await this.request(endpoint);
    }

    async placeOrder(orderData) {
        return await this.request('/api/orders', {
            method: 'POST',
            body: JSON.stringify(orderData)
        });
    }

    async modifyOrder(orderId, orderData) {
        return await this.request(`/api/orders/${orderId}`, {
            method: 'PUT',
            body: JSON.stringify(orderData)
        });
    }

    async cancelOrder(orderId) {
        return await this.request(`/api/orders/${orderId}`, {
            method: 'DELETE'
        });
    }

    // Performance and Analytics APIs
    async getPerformanceMetrics(userId = null, period = '1M') {
        const endpoint = userId
            ? `/api/performance/${userId}/metrics?period=${period}`
            : `/api/performance/metrics?period=${period}`;
        return await this.request(endpoint);
    }

    async getAnalytics(userId = null) {
        const endpoint = userId ? `/api/analytics/${userId}` : '/api/analytics';
        return await this.request(endpoint);
    }

    async getPnLReport(userId = null, startDate = null, endDate = null) {
        let endpoint = userId ? `/api/reports/pnl/${userId}` : '/api/reports/pnl';

        const params = new URLSearchParams();
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);

        if (params.toString()) {
            endpoint += `?${params.toString()}`;
        }

        return await this.request(endpoint);
    }

    // Settings and Configuration APIs
    async getConfig() {
        return await this.request('/api/config');
    }

    async updateConfig(configData) {
        return await this.request('/api/config', {
            method: 'PUT',
            body: JSON.stringify(configData)
        });
    }

    async getSharekhanConfig() {
        return await this.request('/api/config/sharekhan');
    }

    async updateSharekhanConfig(configData) {
        return await this.request('/api/config/sharekhan', {
            method: 'PUT',
            body: JSON.stringify(configData)
        });
    }

    // WebSocket Connection for Real-time Data
    connectWebSocket() {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsURL = `${wsProtocol}//${window.location.host}/ws`;

        this.ws = new WebSocket(wsURL);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.onWebSocketOpen && this.onWebSocketOpen();
        };

        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            } catch (error) {
                console.error('WebSocket message parsing error:', error);
            }
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.onWebSocketError && this.onWebSocketError(error);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.onWebSocketClose && this.onWebSocketClose();

            // Attempt to reconnect after 5 seconds
            setTimeout(() => {
                this.connectWebSocket();
            }, 5000);
        };
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'market_data':
                this.onMarketDataUpdate && this.onMarketDataUpdate(data.payload);
                break;
            case 'order_update':
                this.onOrderUpdate && this.onOrderUpdate(data.payload);
                break;
            case 'position_update':
                this.onPositionUpdate && this.onPositionUpdate(data.payload);
                break;
            case 'system_alert':
                this.onSystemAlert && this.onSystemAlert(data.payload);
                break;
            default:
                console.log('Unknown WebSocket message type:', data.type);
        }
    }

    subscribeToMarketData(symbols) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'subscribe',
                symbols: symbols
            }));
        }
    }

    unsubscribeFromMarketData(symbols) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'unsubscribe',
                symbols: symbols
            }));
        }
    }

    // Utility Methods
    formatError(error) {
        if (error.response) {
            return `Server Error: ${error.response.status} - ${error.response.data?.message || error.response.statusText}`;
        } else if (error.request) {
            return 'Network Error: Unable to reach server';
        } else {
            return `Error: ${error.message}`;
        }
    }

    async retryRequest(requestFn, maxRetries = this.retryCount) {
        for (let i = 0; i < maxRetries; i++) {
            try {
                return await requestFn();
            } catch (error) {
                if (i === maxRetries - 1) throw error;

                // Wait before retry (exponential backoff)
                await new Promise(resolve => setTimeout(resolve, Math.pow(2, i) * 1000));
            }
        }
    }

    // Set auth token
    setAuthToken(token) {
        this.authToken = token;
    }

    // Clear auth token
    clearAuthToken() {
        this.authToken = null;
    }
}

// Create global API instance
const tradingAPI = new TradingAPI();

// Export for use in other scripts
window.tradingAPI = tradingAPI; 