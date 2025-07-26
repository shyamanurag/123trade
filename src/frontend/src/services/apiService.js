import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

class ApiService {
    constructor() {
        this.axiosInstance = axios.create({
            baseURL: API_BASE_URL,
            timeout: 15000,
            headers: {
                'Content-Type': 'application/json',
            },
        })

        // Add auth token to requests
        this.axiosInstance.interceptors.request.use(
            (config) => {
                const token = localStorage.getItem('authToken')
                if (token) {
                    config.headers.Authorization = `Bearer ${token}`
                }
                return config
            },
            (error) => Promise.reject(error)
        )

        // Handle responses and errors
        this.axiosInstance.interceptors.response.use(
            (response) => response,
            (error) => {
                if (error.response?.status === 401) {
                    // Token expired - handled by AuthContext
                    window.dispatchEvent(new CustomEvent('auth:token_expired'))
                }
                return Promise.reject(error)
            }
        )
    }

    // Dashboard APIs
    async getDashboardData() {
        try {
            const response = await this.axiosInstance.get('/v1/dashboard')
            return response.data
        } catch (error) {
            throw new Error(error.response?.data?.message || 'Failed to fetch dashboard data')
        }
    }

    // Market Data APIs
    async getMarketData(symbol = null) {
        try {
            const url = symbol ? `/v1/market-data/${symbol}` : '/v1/market-data'
            const response = await this.axiosInstance.get(url)
            return response.data
        } catch (error) {
            throw new Error(error.response?.data?.message || 'Failed to fetch market data')
        }
    }

    async getLiveIndices() {
        try {
            const response = await this.axiosInstance.get('/v1/market-data/indices')
            return response.data
        } catch (error) {
            throw new Error(error.response?.data?.message || 'Failed to fetch live indices')
        }
    }

    // Trading APIs
    async getTrades(params = {}) {
        try {
            const response = await this.axiosInstance.get('/v1/trades', { params })
            return response.data
        } catch (error) {
            throw new Error(error.response?.data?.message || 'Failed to fetch trades')
        }
    }

    async getTradeDetails(tradeId) {
        try {
            const response = await this.axiosInstance.get(`/v1/trades/${tradeId}`)
            return response.data
        } catch (error) {
            throw new Error(error.response?.data?.message || 'Failed to fetch trade details')
        }
    }

    async submitTrade(tradeData) {
        try {
            const response = await this.axiosInstance.post('/v1/trades', tradeData)
            return response.data
        } catch (error) {
            throw new Error(error.response?.data?.message || 'Failed to submit trade')
        }
    }

    // Analytics APIs
    async getAnalytics(timeframe = '1d') {
        try {
            const response = await this.axiosInstance.get('/v1/analytics', {
                params: { timeframe }
            })
            return response.data
        } catch (error) {
            throw new Error(error.response?.data?.message || 'Failed to fetch analytics')
        }
    }

    async getPerformanceMetrics() {
        try {
            const response = await this.axiosInstance.get('/v1/analytics/performance')
            return response.data
        } catch (error) {
            throw new Error(error.response?.data?.message || 'Failed to fetch performance metrics')
        }
    }

    // User Management APIs
    async getUsers(params = {}) {
        try {
            const response = await this.axiosInstance.get('/v1/users', { params })
            return response.data
        } catch (error) {
            throw new Error(error.response?.data?.message || 'Failed to fetch users')
        }
    }

    async createUser(userData) {
        try {
            const response = await this.axiosInstance.post('/v1/users', userData)
            return response.data
        } catch (error) {
            throw new Error(error.response?.data?.message || 'Failed to create user')
        }
    }

    async updateUser(userId, updates) {
        try {
            const response = await this.axiosInstance.put(`/v1/users/${userId}`, updates)
            return response.data
        } catch (error) {
            throw new Error(error.response?.data?.message || 'Failed to update user')
        }
    }

    async deleteUser(userId) {
        try {
            const response = await this.axiosInstance.delete(`/v1/users/${userId}`)
            return response.data
        } catch (error) {
            throw new Error(error.response?.data?.message || 'Failed to delete user')
        }
    }

    // Multi-User API Submission
    async submitMultiUserAPI(apiData) {
        try {
            const response = await this.axiosInstance.post('/v1/multi-user-api', apiData)
            return response.data
        } catch (error) {
            throw new Error(error.response?.data?.message || 'Failed to submit multi-user API')
        }
    }

    async getMultiUserAPIStatus() {
        try {
            const response = await this.axiosInstance.get('/v1/multi-user-api/status')
            return response.data
        } catch (error) {
            throw new Error(error.response?.data?.message || 'Failed to fetch API status')
        }
    }

    // Token Management APIs
    async submitDailyToken(tokenData) {
        try {
            const response = await this.axiosInstance.post('/v1/auth-tokens/daily', tokenData)
            return response.data
        } catch (error) {
            throw new Error(error.response?.data?.message || 'Failed to submit daily token')
        }
    }

    async getTokenStatus() {
        try {
            const response = await this.axiosInstance.get('/v1/auth-tokens/status')
            return response.data
        } catch (error) {
            throw new Error(error.response?.data?.message || 'Failed to fetch token status')
        }
    }

    async getAllUserTokens() {
        try {
            const response = await this.axiosInstance.get('/v1/auth-tokens/all-users')
            return response.data
        } catch (error) {
            throw new Error(error.response?.data?.message || 'Failed to fetch user tokens')
        }
    }

    // System Health APIs
    async getSystemHealth() {
        try {
            const response = await this.axiosInstance.get('/health')
            return response.data
        } catch (error) {
            throw new Error(error.response?.data?.message || 'Failed to fetch system health')
        }
    }

    async getTruedataStatus() {
        try {
            const response = await this.axiosInstance.get('/v1/truedata/status')
            return response.data
        } catch (error) {
            throw new Error(error.response?.data?.message || 'Failed to fetch TrueData status')
        }
    }
}

export const apiService = new ApiService() 