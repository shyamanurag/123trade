import React, { createContext, useContext, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { authService } from '../services/authService'

const AuthContext = createContext()

export const useAuth = () => {
    const context = useContext(AuthContext)
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider')
    }
    return context
}

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null)
    const [loading, setLoading] = useState(true)
    const [authToken, setAuthToken] = useState(null)
    const [tokenExpiry, setTokenExpiry] = useState(null)

    useEffect(() => {
        const initAuth = async () => {
            try {
                const token = localStorage.getItem('authToken')
                const userData = localStorage.getItem('userData')

                if (token && userData) {
                    setAuthToken(token)
                    setUser(JSON.parse(userData))

                    // Check if token is still valid
                    const isValid = await authService.validateToken(token)
                    if (!isValid) {
                        await logout()
                    }
                }
            } catch (error) {
                console.error('Auth initialization error:', error)
                await logout()
            } finally {
                setLoading(false)
            }
        }

        initAuth()
    }, [])

    const login = async (credentials) => {
        try {
            setLoading(true)
            const response = await authService.login(credentials)

            const { user: userData, token, expires_at } = response

            setUser(userData)
            setAuthToken(token)
            setTokenExpiry(expires_at)

            localStorage.setItem('authToken', token)
            localStorage.setItem('userData', JSON.stringify(userData))
            localStorage.setItem('tokenExpiry', expires_at)

            toast.success('Login successful!')
            return response
        } catch (error) {
            toast.error(error.message || 'Login failed')
            throw error
        } finally {
            setLoading(false)
        }
    }

    const logout = async () => {
        try {
            if (authToken) {
                await authService.logout(authToken)
            }
        } catch (error) {
            console.error('Logout error:', error)
        } finally {
            setUser(null)
            setAuthToken(null)
            setTokenExpiry(null)

            localStorage.removeItem('authToken')
            localStorage.removeItem('userData')
            localStorage.removeItem('tokenExpiry')

            toast.success('Logged out successfully')
        }
    }

    const refreshToken = async () => {
        try {
            const response = await authService.refreshToken(authToken)
            const { token, expires_at } = response

            setAuthToken(token)
            setTokenExpiry(expires_at)

            localStorage.setItem('authToken', token)
            localStorage.setItem('tokenExpiry', expires_at)

            return token
        } catch (error) {
            console.error('Token refresh failed:', error)
            await logout()
            throw error
        }
    }

    const updateUserProfile = (updates) => {
        const updatedUser = { ...user, ...updates }
        setUser(updatedUser)
        localStorage.setItem('userData', JSON.stringify(updatedUser))
    }

    const value = {
        user,
        authToken,
        tokenExpiry,
        loading,
        login,
        logout,
        refreshToken,
        updateUserProfile
    }

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    )
} 