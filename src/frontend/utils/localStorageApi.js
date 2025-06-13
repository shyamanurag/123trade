/**
 * Local Storage API Utility
 * Provides persistent data storage for local development
 */

const LOCAL_STORAGE_KEYS = {
    RECOMMENDATIONS: 'trading_recommendations',
    USERS: 'trading_users',
    PERFORMANCE: 'trading_performance',
    SETTINGS: 'trading_settings'
};

class LocalStorageAPI {
    constructor() {
        this.isSupported = this.checkSupport();
    }

    checkSupport() {
        try {
            const test = '__localStorage_test__';
            localStorage.setItem(test, test);
            localStorage.removeItem(test);
            return true;
        } catch (e) {
            return false;
        }
    }

    // Generic storage methods
    setItem(key, data) {
        if (!this.isSupported) return false;
        try {
            localStorage.setItem(key, JSON.stringify({
                data,
                timestamp: Date.now()
            }));
            return true;
        } catch (e) {
            console.error('Failed to save to localStorage:', e);
            return false;
        }
    }

    getItem(key, maxAge = null) {
        if (!this.isSupported) return null;
        try {
            const item = localStorage.getItem(key);
            if (!item) return null;

            const parsed = JSON.parse(item);

            // Check if data is too old
            if (maxAge && Date.now() - parsed.timestamp > maxAge) {
                localStorage.removeItem(key);
                return null;
            }

            return parsed.data;
        } catch (e) {
            console.error('Failed to read from localStorage:', e);
            return null;
        }
    }

    removeItem(key) {
        if (!this.isSupported) return false;
        try {
            localStorage.removeItem(key);
            return true;
        } catch (e) {
            console.error('Failed to remove from localStorage:', e);
            return false;
        }
    }

    // Recommendations methods
    saveRecommendations(recommendations) {
        return this.setItem(LOCAL_STORAGE_KEYS.RECOMMENDATIONS, recommendations);
    }

    getRecommendations() {
        return this.getItem(LOCAL_STORAGE_KEYS.RECOMMENDATIONS, 30 * 60 * 1000); // 30 minutes
    }

    // Users methods
    saveUsers(users) {
        return this.setItem(LOCAL_STORAGE_KEYS.USERS, users);
    }

    getUsers() {
        return this.getItem(LOCAL_STORAGE_KEYS.USERS);
    }

    addUser(user) {
        const users = this.getUsers() || [];
        users.push(user);
        return this.saveUsers(users);
    }

    updateUser(userId, updatedUser) {
        const users = this.getUsers() || [];
        const index = users.findIndex(u => u.user_id === userId);
        if (index !== -1) {
            users[index] = { ...users[index], ...updatedUser };
            return this.saveUsers(users);
        }
        return false;
    }

    deleteUser(userId) {
        const users = this.getUsers() || [];
        const filteredUsers = users.filter(u => u.user_id !== userId);
        return this.saveUsers(filteredUsers);
    }

    // Performance methods
    savePerformanceData(data) {
        return this.setItem(LOCAL_STORAGE_KEYS.PERFORMANCE, data);
    }

    getPerformanceData() {
        return this.getItem(LOCAL_STORAGE_KEYS.PERFORMANCE, 60 * 60 * 1000); // 1 hour
    }

    // Settings methods
    saveSettings(settings) {
        return this.setItem(LOCAL_STORAGE_KEYS.SETTINGS, settings);
    }

    getSettings() {
        return this.getItem(LOCAL_STORAGE_KEYS.SETTINGS);
    }

    // Utility methods
    clearAll() {
        Object.values(LOCAL_STORAGE_KEYS).forEach(key => {
            this.removeItem(key);
        });
    }

    getStorageInfo() {
        if (!this.isSupported) return { supported: false };

        const usage = {};
        let totalSize = 0;

        Object.entries(LOCAL_STORAGE_KEYS).forEach(([name, key]) => {
            const item = localStorage.getItem(key);
            const size = item ? new Blob([item]).size : 0;
            usage[name] = {
                key,
                size,
                exists: !!item,
                lastModified: item ? JSON.parse(item).timestamp : null
            };
            totalSize += size;
        });

        return {
            supported: true,
            usage,
            totalSize,
            available: this.getAvailableSpace()
        };
    }

    getAvailableSpace() {
        try {
            // Try to estimate available space
            const testKey = '__space_test__';
            let size = 0;

            // Test with increasing sizes until we hit the limit
            for (let i = 0; i < 10; i++) {
                try {
                    const testData = new Array(1024 * 1024).join('x'); // 1MB of data
                    localStorage.setItem(testKey, testData);
                    localStorage.removeItem(testKey);
                    size += 1024 * 1024;
                } catch (e) {
                    break;
                }
            }

            return size;
        } catch (e) {
            return 0;
        }
    }
}

// Create and export singleton instance
const localStorageAPI = new LocalStorageAPI();

export default localStorageAPI; 