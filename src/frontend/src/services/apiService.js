import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://trade123-l3zp7.ondigitalocean.app'

class ApiService {
    constructor() {
        this.client = axios.create({
            baseURL: API_BASE_URL,
            timeout: 30000,
            headers: {
                'Content-Type': 'application/json',
            },
        })

        // Request interceptor to add auth token
        this.client.interceptors.request.use(
            (config) => {
                const token = localStorage.getItem('access_token')
                if (token) {
                    config.headers.Authorization = `Bearer ${token}`
                }
                return config
            },
            (error) => {
                return Promise.reject(error)
            }
        )

        // Response interceptor for token refresh
        this.client.interceptors.response.use(
            (response) => response,
            async (error) => {
                const originalRequest = error.config

                if (error.response?.status === 401 && !originalRequest._retry) {
                    originalRequest._retry = true

                    try {
                        const refreshToken = localStorage.getItem('refresh_token')
                        if (refreshToken) {
                            const response = await this.client.post('/auth/refresh', {
                                refresh_token: refreshToken
                            })

                            const { access_token } = response.data
                            localStorage.setItem('access_token', access_token)

                            originalRequest.headers.Authorization = `Bearer ${access_token}`
                            return this.client(originalRequest)
                        }
                    } catch (refreshError) {
                        // Refresh failed, redirect to login
                        localStorage.removeItem('access_token')
                        localStorage.removeItem('refresh_token')
                        window.location.href = '/login'
                        return Promise.reject(refreshError)
                    }
                }

                return Promise.reject(error)
            }
        )
    }

    // Dashboard API
    async getDashboardData() {
        const response = await this.client.get('/api/dashboard')
        return response.data
    }

    // Authentication API
    async login(credentials) {
        const response = await this.client.post('/auth/login', credentials)
        return response.data
    }

    async logout() {
        const response = await this.client.post('/auth/logout')
        return response.data
    }

    async refreshToken(refreshToken) {
        const response = await this.client.post('/auth/refresh', {
            refresh_token: refreshToken
        })
        return response.data
    }

    async validateToken() {
        const response = await this.client.get('/auth/validate')
        return response.data
    }

    async getCurrentUser() {
        const response = await this.client.get('/auth/me')
        return response.data
    }

    // Users API
    async getUsers() {
        const response = await this.client.get('/v1/users/')
        return response.data
    }

    async getUser(userId) {
        const response = await this.client.get(`/v1/users/${userId}`)
        return response.data
    }

    async createUser(userData) {
        const response = await this.client.post('/v1/users/', userData)
        return response.data
    }

    async updateUser(userId, userData) {
        const response = await this.client.put(`/v1/users/${userId}`, userData)
        return response.data
    }

    async deleteUser(userId) {
        const response = await this.client.delete(`/v1/users/${userId}`)
        return response.data
    }

    // Token Management API
    async submitDailyToken(tokenData) {
        const response = await this.client.post('/v1/auth-tokens/daily', tokenData)
        return response.data
    }

    async getTokenStatus() {
        const response = await this.client.get('/v1/auth-tokens/status')
        return response.data
    }

    async getAllUsersTokenStatus() {
        const response = await this.client.get('/v1/auth-tokens/all-users')
        return response.data
    }

    // Trading API
    async getTrades() {
        const response = await this.client.get('/api/trades')
        return response.data
    }

    async createTrade(tradeData) {
        const response = await this.client.post('/api/trades', tradeData)
        return response.data
    }

    async getTrade(tradeId) {
        const response = await this.client.get(`/api/trades/${tradeId}`)
        return response.data
    }

    // Market Data API
    async getMarketData() {
        const response = await this.client.get('/api/market/data')
        return response.data
    }

    async getIndices() {
        const response = await this.client.get('/api/market/indices')
        return response.data
    }

    // Multi-User API
    async submitMultiUserRequest(requestData) {
        const response = await this.client.post('/api/multi-user/submit', requestData)
        return response.data
    }

    async getMultiUserRequests() {
        const response = await this.client.get('/api/multi-user/requests')
        return response.data
    }

    // ShareKhan API
    async getShareKhanData() {
        const response = await this.client.get('/api/sharekhan/data')
        return response.data
    }

    async submitShareKhanOrder(orderData) {
        const response = await this.client.post('/api/sharekhan/order', orderData)
        return response.data
    }

    // System API
    async getSystemHealth() {
        const response = await this.client.get('/health')
        return response.data
    }

    async getSystemConfig() {
        const response = await this.client.get('/api/system/config')
        return response.data
    }

    // Analytics API
    async getAnalytics(params = {}) {
        const response = await this.client.get('/api/analytics', { params })
        return response.data
    }

    async getPerformanceMetrics() {
        const response = await this.client.get('/api/analytics/performance')
        return response.data
    }
}

export const apiService = new ApiService()
export default apiService 