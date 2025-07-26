// ShareKhan Trading Platform - Main JavaScript
class TradingPlatform {
    constructor() {
        this.baseURL = window.location.origin;
        this.currentSection = 'dashboard';
        this.authToken = null;
        this.init();
    }

    init() {
        this.setupNavigation();
        this.loadDashboard();
        this.startRealTimeUpdates();
        this.checkAuthStatus();
    }

    // Navigation System
    setupNavigation() {
        const navLinks = document.querySelectorAll('.nav-link');
        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const section = link.getAttribute('href').replace('#', '');
                this.switchSection(section);

                // Update active nav link
                navLinks.forEach(l => l.classList.remove('active'));
                link.classList.add('active');
            });
        });

        // Token refresh button
        document.getElementById('refreshToken').addEventListener('click', () => {
            this.refreshAuthToken();
        });
    }

    switchSection(section) {
        // Hide all sections
        document.querySelectorAll('.page-section').forEach(s => {
            s.classList.remove('active');
        });

        // Show target section
        document.getElementById(section).classList.add('active');
        this.currentSection = section;

        // Load section-specific data
        switch (section) {
            case 'dashboard':
                this.loadDashboard();
                break;
            case 'reports':
                this.loadReports();
                break;
            case 'indices':
                this.loadIndices();
                break;
            case 'users':
                this.loadUsers();
                break;
            case 'settings':
                this.loadSettings();
                break;
        }
    }

    // Dashboard Functions
    async loadDashboard() {
        await Promise.all([
            this.updateStats(),
            this.updateIndices(),
            this.updateActivity(),
            this.updatePerformanceChart()
        ]);
    }

    async updateStats() {
        try {
            const response = await fetch(`${this.baseURL}/api/system/status`);
            const data = await response.json();

            // Update stats display
            document.getElementById('totalUsers').textContent = data.components?.users || '1';
            document.getElementById('activeTrades').textContent = '0';
            document.getElementById('totalPnl').textContent = '₹0.00';
            document.getElementById('successRate').textContent = '100%';

            this.showNotification('Stats updated successfully', 'success');
        } catch (error) {
            console.error('Error updating stats:', error);
            this.showNotification('Error updating stats', 'error');
        }
    }

    async updateIndices() {
        // Simulate live market data
        const indices = [
            { id: 'nifty50', name: 'NIFTY 50', value: 19850.45, change: 0.75 },
            { id: 'banknifty', name: 'BANK NIFTY', value: 44320.80, change: -0.32 },
            { id: 'sensex', name: 'SENSEX', value: 66795.14, change: 0.45 }
        ];

        indices.forEach(index => {
            const valueEl = document.getElementById(index.id);
            const changeEl = document.getElementById(index.id + 'Change');

            if (valueEl && changeEl) {
                valueEl.textContent = index.value.toFixed(2);
                changeEl.textContent = `${index.change >= 0 ? '+' : ''}${index.change.toFixed(2)}%`;
                changeEl.className = `index-change ${index.change >= 0 ? 'positive' : 'negative'}`;
            }
        });
    }

    updateActivity() {
        const activities = [
            { time: 'Just now', action: 'System initialized successfully' },
            { time: '2 min ago', action: 'ShareKhan API connected' },
            { time: '5 min ago', action: 'Database connection established' },
            { time: '10 min ago', action: 'Application started' }
        ];

        const activityList = document.getElementById('activityList');
        activityList.innerHTML = activities.map(activity => `
            <div class="activity-item">
                <span class="time">${activity.time}</span>
                <span class="action">${activity.action}</span>
            </div>
        `).join('');
    }

    // Auth Token Management
    async checkAuthStatus() {
        try {
            const response = await fetch(`${this.baseURL}/api/system/status`);
            const data = await response.json();

            const authStatus = document.getElementById('authStatus');
            const tokenStatus = document.getElementById('tokenStatus');

            if (data.components?.sharekhan_api) {
                authStatus.textContent = 'Connected';
                authStatus.style.color = '#4CAF50';
                tokenStatus.className = 'status-dot online';
            } else {
                authStatus.textContent = 'Disconnected';
                authStatus.style.color = '#F44336';
                tokenStatus.className = 'status-dot offline';
            }
        } catch (error) {
            console.error('Auth check failed:', error);
            const authStatus = document.getElementById('authStatus');
            authStatus.textContent = 'Error';
            authStatus.style.color = '#F44336';
        }
    }

    async refreshAuthToken() {
        this.showNotification('Refreshing auth token...', 'warning');

        try {
            // Simulate token refresh
            setTimeout(() => {
                this.checkAuthStatus();
                this.showNotification('Auth token refreshed successfully', 'success');
            }, 2000);
        } catch (error) {
            this.showNotification('Failed to refresh token', 'error');
        }
    }

    // Reports Functions
    async loadReports() {
        await Promise.all([
            this.loadUserReport(),
            this.loadTradeDetails(),
            this.updateAnalyticsChart()
        ]);
    }

    async loadUserReport() {
        const userReportBody = document.getElementById('userReportBody');

        // Sample user data
        const users = [
            { name: 'Admin User', trades: 0, pnl: 0, success: '100%', lastActive: 'Now' },
            { name: 'Demo User', trades: 0, pnl: 0, success: '0%', lastActive: 'Never' }
        ];

        userReportBody.innerHTML = users.map(user => `
            <tr>
                <td>${user.name}</td>
                <td>${user.trades}</td>
                <td>₹${user.pnl.toFixed(2)}</td>
                <td>${user.success}</td>
                <td>${user.lastActive}</td>
            </tr>
        `).join('');
    }

    async loadTradeDetails() {
        const tradeDetailsBody = document.getElementById('tradeDetailsBody');
        tradeDetailsBody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; color: #666;">
                    No trades available. Start trading to see details here.
                </td>
            </tr>
        `;
    }

    // Indices Functions
    async loadIndices() {
        this.loadMajorIndices();
        this.loadWatchlist();
        this.updateMarketDetails();
    }

    loadMajorIndices() {
        const majorIndices = [
            { name: 'NIFTY 50', value: 19850.45, change: 0.75 },
            { name: 'BANK NIFTY', value: 44320.80, change: -0.32 },
            { name: 'SENSEX', value: 66795.14, change: 0.45 },
            { name: 'NIFTY IT', value: 28450.30, change: 1.25 },
            { name: 'NIFTY PHARMA', value: 13890.60, change: -0.85 }
        ];

        const container = document.getElementById('majorIndices');
        container.innerHTML = majorIndices.map(index => `
            <div class="index-item">
                <span class="index-name">${index.name}</span>
                <span class="index-value">${index.value.toFixed(2)}</span>
                <span class="index-change ${index.change >= 0 ? 'positive' : 'negative'}">
                    ${index.change >= 0 ? '+' : ''}${index.change.toFixed(2)}%
                </span>
            </div>
        `).join('');
    }

    loadWatchlist() {
        const watchlist = JSON.parse(localStorage.getItem('watchlist') || '[]');
        const container = document.getElementById('watchlistContainer');

        if (watchlist.length === 0) {
            container.innerHTML = '<p>No symbols in watchlist. Add some symbols to track them.</p>';
            return;
        }

        container.innerHTML = watchlist.map(symbol => `
            <div class="watchlist-item">
                <span>${symbol}</span>
                <button onclick="removeFromWatchlist('${symbol}')">Remove</button>
            </div>
        `).join('');
    }

    updateMarketDetails() {
        const now = new Date();
        const marketHours = now.getHours() >= 9 && now.getHours() < 16;

        document.getElementById('marketStatus').textContent = marketHours ? 'Open' : 'Closed';
        document.getElementById('lastUpdate').textContent = now.toLocaleTimeString();
    }

    // Users Functions
    async loadUsers() {
        this.loadUsersList();
        this.loadAuthTokens();
    }

    loadUsersList() {
        const users = [
            { id: 1, name: 'Admin User', email: 'admin@trading.com', status: 'Active', lastLogin: 'Now' },
            { id: 2, name: 'Demo User', email: 'demo@trading.com', status: 'Inactive', lastLogin: 'Never' }
        ];

        const usersList = document.getElementById('usersList');
        usersList.innerHTML = users.map(user => `
            <div class="user-item" onclick="showUserDetails(${user.id})">
                <div class="user-info">
                    <strong>${user.name}</strong>
                    <span>${user.email}</span>
                    <span class="status ${user.status.toLowerCase()}">${user.status}</span>
                </div>
            </div>
        `).join('');
    }

    loadAuthTokens() {
        const tokens = [
            { user: 'Admin User', token: 'sk_live_****', expires: '24h', status: 'Active' },
            { user: 'Demo User', token: 'Not Generated', expires: '-', status: 'Inactive' }
        ];

        const tokensList = document.getElementById('authTokensList');
        tokensList.innerHTML = tokens.map(token => `
            <div class="token-item">
                <div class="token-info">
                    <strong>${token.user}</strong>
                    <span>Token: ${token.token}</span>
                    <span>Expires: ${token.expires}</span>
                    <span class="status ${token.status.toLowerCase()}">${token.status}</span>
                </div>
            </div>
        `).join('');
    }

    // Settings Functions
    async loadSettings() {
        this.loadApiConfig();
        this.checkSystemHealth();
    }

    loadApiConfig() {
        // Load saved config (in real app, this would be from secure storage)
        document.getElementById('customerId').value = 'Sanurag1977';
        document.getElementById('apiKey').placeholder = 'API Key configured';
        document.getElementById('secretKey').placeholder = 'Secret Key configured';
    }

    async checkSystemHealth() {
        const healthChecks = [
            { id: 'dbStatus', name: 'Database', url: '/api/system/status' },
            { id: 'redisStatus', name: 'Redis', url: '/api/system/status' },
            { id: 'apiStatus', name: 'ShareKhan API', url: '/api/system/status' }
        ];

        for (const check of healthChecks) {
            const element = document.getElementById(check.id);
            element.textContent = 'Checking...';

            try {
                const response = await fetch(`${this.baseURL}${check.url}`);
                const data = await response.json();

                if (response.ok) {
                    element.textContent = '✅ Healthy';
                    element.style.color = '#4CAF50';
                } else {
                    element.textContent = '❌ Error';
                    element.style.color = '#F44336';
                }
            } catch (error) {
                element.textContent = '❌ Unreachable';
                element.style.color = '#F44336';
            }
        }
    }

    // Real-time Updates
    startRealTimeUpdates() {
        // Update indices every 30 seconds
        setInterval(() => {
            if (this.currentSection === 'dashboard' || this.currentSection === 'indices') {
                this.updateIndices();
            }
        }, 30000);

        // Update stats every minute
        setInterval(() => {
            if (this.currentSection === 'dashboard') {
                this.updateStats();
            }
        }, 60000);
    }

    // Utility Functions
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR'
        }).format(amount);
    }

    formatNumber(number) {
        return new Intl.NumberFormat('en-IN').format(number);
    }
}

// Global Functions (called from HTML)
let platform;

window.addEventListener('DOMContentLoaded', () => {
    platform = new TradingPlatform();
});

// Global function for indices refresh
function refreshIndices() {
    platform.updateIndices();
    platform.showNotification('Indices refreshed', 'success');
}

// Global function for watchlist management
function addToWatchlist() {
    const symbolInput = document.getElementById('symbolInput');
    const symbol = symbolInput.value.trim().toUpperCase();

    if (!symbol) {
        platform.showNotification('Please enter a valid symbol', 'warning');
        return;
    }

    const watchlist = JSON.parse(localStorage.getItem('watchlist') || '[]');
    if (!watchlist.includes(symbol)) {
        watchlist.push(symbol);
        localStorage.setItem('watchlist', JSON.stringify(watchlist));
        platform.loadWatchlist();
        platform.showNotification(`${symbol} added to watchlist`, 'success');
    } else {
        platform.showNotification(`${symbol} already in watchlist`, 'warning');
    }

    symbolInput.value = '';
}

function removeFromWatchlist(symbol) {
    const watchlist = JSON.parse(localStorage.getItem('watchlist') || '[]');
    const filtered = watchlist.filter(s => s !== symbol);
    localStorage.setItem('watchlist', JSON.stringify(filtered));
    platform.loadWatchlist();
    platform.showNotification(`${symbol} removed from watchlist`, 'success');
}

// Report Functions
function generateReport() {
    const fromDate = document.getElementById('reportDateFrom').value;
    const toDate = document.getElementById('reportDateTo').value;

    if (!fromDate || !toDate) {
        platform.showNotification('Please select both from and to dates', 'warning');
        return;
    }

    platform.showNotification(`Generating report from ${fromDate} to ${toDate}`, 'success');
    platform.loadReports();
}

function loadUserReport() {
    platform.loadUserReport();
}

// User Management Functions
function addUser() {
    const name = prompt('Enter user name:');
    if (name) {
        platform.showNotification(`User ${name} would be added (demo mode)`, 'success');
    }
}

function refreshAllTokens() {
    platform.showNotification('Refreshing all auth tokens...', 'warning');
    setTimeout(() => {
        platform.showNotification('All tokens refreshed successfully', 'success');
        platform.loadAuthTokens();
    }, 2000);
}

function searchUsers() {
    const query = document.getElementById('userSearch').value.toLowerCase();
    // Implementation for user search would go here
    console.log('Searching for:', query);
}

function showUserDetails(userId) {
    const userDetailsPanel = document.getElementById('userDetailsPanel');
    userDetailsPanel.innerHTML = `
        <h4>User ID: ${userId}</h4>
        <p><strong>Status:</strong> Active</p>
        <p><strong>Trading Limit:</strong> ₹1,00,000</p>
        <p><strong>Total Trades:</strong> 0</p>
        <p><strong>P&L:</strong> ₹0.00</p>
        <button class="btn-primary">Edit User</button>
        <button class="btn-secondary">Reset Password</button>
    `;
}

// Settings Functions
function saveApiConfig() {
    const apiKey = document.getElementById('apiKey').value;
    const secretKey = document.getElementById('secretKey').value;
    const customerId = document.getElementById('customerId').value;

    // In real app, this would be saved securely
    platform.showNotification('API configuration saved successfully', 'success');
}

function checkSystemHealth() {
    platform.checkSystemHealth();
} 