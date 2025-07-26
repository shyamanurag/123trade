import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

class AuthService {
    constructor() {
        this.axiosInstance = axios.create({
            baseURL: API_BASE_URL,
            timeout: 10000,
            headers: {
                'Content-Type': 'application/json',
            },
        })

        // Request interceptor to add auth token
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

        // Response interceptor to handle token expiry
        this.axiosInstance.interceptors.response.use(
            (response) => response,
            async (error) => {
                if (error.response?.status === 401) {
                    // Token expired or invalid
                    localStorage.removeItem('authToken')
                    localStorage.removeItem('userData')
                    localStorage.removeItem('tokenExpiry')
                    window.location.href = '/login'
                }
                return Promise.reject(error)
            }
        )
    }

    async login(credentials) {
        try {
            const response = await this.axiosInstance.post('/auth/login', credentials)
            return response.data
        } catch (error) {
            throw new Error(error.response?.data?.message || 'Login failed')
        }
    }

    async logout(token) {
        try {
            await this.axiosInstance.post('/auth/logout', { token })
        } catch (error) {
            console.error('Logout error:', error)
        }
    }

    async validateToken(token) {
        try {
            const response = await this.axiosInstance.post('/auth/validate', { token })
            return response.data.valid
        } catch (error) {
            return false
        }
    }

    async refreshToken(token) {
        try {
            const response = await this.axiosInstance.post('/auth/refresh', { token })
            return response.data
        } catch (error) {
            throw new Error(error.response?.data?.message || 'Token refresh failed')
        }
    }

    async register(userData) {
        try {
            const response = await this.axiosInstance.post('/auth/register', userData)
            return response.data
        } catch (error) {
            throw new Error(error.response?.data?.message || 'Registration failed')
        }
    }

    async forgotPassword(email) {
        try {
            const response = await this.axiosInstance.post('/auth/forgot-password', { email })
            return response.data
        } catch (error) {
            throw new Error(error.response?.data?.message || 'Password reset failed')
        }
    }

    async resetPassword(token, newPassword) {
        try {
            const response = await this.axiosInstance.post('/auth/reset-password', {
                token,
                password: newPassword
            })
            return response.data
        } catch (error) {
            throw new Error(error.response?.data?.message || 'Password reset failed')
        }
    }

    async updateProfile(updates) {
        try {
            const response = await this.axiosInstance.put('/auth/profile', updates)
            return response.data
        } catch (error) {
            throw new Error(error.response?.data?.message || 'Profile update failed')
        }
    }

    async changePassword(currentPassword, newPassword) {
        try {
            const response = await this.axiosInstance.post('/auth/change-password', {
                current_password: currentPassword,
                new_password: newPassword
            })
            return response.data
        } catch (error) {
            throw new Error(error.response?.data?.message || 'Password change failed')
        }
    }

    // Zerodha-specific auth methods
    async getZerodhaAuthUrl() {
        try {
            const response = await this.axiosInstance.get('/auth/zerodha/url')
            return response.data
        } catch (error) {
            throw new Error(error.response?.data?.message || 'Failed to get Zerodha auth URL')
        }
    }

    async submitZerodhaToken(token, requestToken) {
        try {
            const response = await this.axiosInstance.post('/auth/zerodha/token', {
                token,
                request_token: requestToken
            })
            return response.data
        } catch (error) {
            throw new Error(error.response?.data?.message || 'Zerodha token submission failed')
        }
    }

    async getZerodhaStatus() {
        try {
            const response = await this.axiosInstance.get('/auth/zerodha/status')
            return response.data
        } catch (error) {
            throw new Error(error.response?.data?.message || 'Failed to get Zerodha status')
        }
    }

    async refreshZerodhaToken() {
        try {
            const response = await this.axiosInstance.post('/auth/zerodha/refresh')
            return response.data
        } catch (error) {
            throw new Error(error.response?.data?.message || 'Zerodha token refresh failed')
        }
    }
}

export const authService = new AuthService() 