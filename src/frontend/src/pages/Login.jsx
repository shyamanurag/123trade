import { motion } from 'framer-motion'
import { Activity, Eye, EyeOff, Lock, Mail } from 'lucide-react'
import React, { useState } from 'react'
import toast from 'react-hot-toast'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import { useAuth } from '../context/AuthContext'

const Login = () => {
    const { login, loading } = useAuth()
    const [formData, setFormData] = useState({
        email: '',
        password: ''
    })
    const [showPassword, setShowPassword] = useState(false)
    const [errors, setErrors] = useState({})

    const validateForm = () => {
        const newErrors = {}

        if (!formData.email) {
            newErrors.email = 'Email is required'
        } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
            newErrors.email = 'Email is invalid'
        }

        if (!formData.password) {
            newErrors.password = 'Password is required'
        } else if (formData.password.length < 6) {
            newErrors.password = 'Password must be at least 6 characters'
        }

        setErrors(newErrors)
        return Object.keys(newErrors).length === 0
    }

    const handleSubmit = async (e) => {
        e.preventDefault()

        if (!validateForm()) {
            return
        }

        try {
            await login(formData)
            toast.success('Welcome to Trade123!')
        } catch (error) {
            // Error is already handled in the auth context
            console.error('Login error:', error)
        }
    }

    const handleChange = (e) => {
        const { name, value } = e.target
        setFormData(prev => ({
            ...prev,
            [name]: value
        }))

        // Clear error when user starts typing
        if (errors[name]) {
            setErrors(prev => ({
                ...prev,
                [name]: ''
            }))
        }
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 via-white to-primary-50 py-12 px-4 sm:px-6 lg:px-8">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
                className="max-w-md w-full space-y-8"
            >
                {/* Header */}
                <div className="text-center">
                    <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
                        className="mx-auto w-16 h-16 bg-gradient-to-br from-primary-500 to-primary-700 rounded-xl flex items-center justify-center shadow-lg"
                    >
                        <Activity className="w-8 h-8 text-white" />
                    </motion.div>

                    <motion.h1
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.3 }}
                        className="mt-6 text-3xl font-bold text-gray-900"
                    >
                        Welcome to Trade123
                    </motion.h1>

                    <motion.p
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.4 }}
                        className="mt-2 text-sm text-gray-600"
                    >
                        Sign in to access your advanced trading platform
                    </motion.p>
                </div>

                {/* Login Form */}
                <motion.form
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.5 }}
                    className="mt-8 space-y-6"
                    onSubmit={handleSubmit}
                >
                    <div className="space-y-4">
                        {/* Email Field */}
                        <div>
                            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                                Email Address
                            </label>
                            <div className="relative">
                                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                    <Mail className="h-5 w-5 text-gray-400" />
                                </div>
                                <input
                                    id="email"
                                    name="email"
                                    type="email"
                                    autoComplete="email"
                                    value={formData.email}
                                    onChange={handleChange}
                                    className={`input-field pl-10 ${errors.email ? 'border-danger-300 focus:ring-danger-500' : ''}`}
                                    placeholder="Enter your email"
                                />
                            </div>
                            {errors.email && (
                                <motion.p
                                    initial={{ opacity: 0, height: 0 }}
                                    animate={{ opacity: 1, height: 'auto' }}
                                    className="mt-1 text-sm text-danger-600"
                                >
                                    {errors.email}
                                </motion.p>
                            )}
                        </div>

                        {/* Password Field */}
                        <div>
                            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                                Password
                            </label>
                            <div className="relative">
                                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                    <Lock className="h-5 w-5 text-gray-400" />
                                </div>
                                <input
                                    id="password"
                                    name="password"
                                    type={showPassword ? 'text' : 'password'}
                                    autoComplete="current-password"
                                    value={formData.password}
                                    onChange={handleChange}
                                    className={`input-field pl-10 pr-10 ${errors.password ? 'border-danger-300 focus:ring-danger-500' : ''}`}
                                    placeholder="Enter your password"
                                />
                                <button
                                    type="button"
                                    className="absolute inset-y-0 right-0 pr-3 flex items-center"
                                    onClick={() => setShowPassword(!showPassword)}
                                >
                                    {showPassword ? (
                                        <EyeOff className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                                    ) : (
                                        <Eye className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                                    )}
                                </button>
                            </div>
                            {errors.password && (
                                <motion.p
                                    initial={{ opacity: 0, height: 0 }}
                                    animate={{ opacity: 1, height: 'auto' }}
                                    className="mt-1 text-sm text-danger-600"
                                >
                                    {errors.password}
                                </motion.p>
                            )}
                        </div>
                    </div>

                    {/* Submit Button */}
                    <div>
                        <motion.button
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            type="submit"
                            disabled={loading}
                            className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-lg text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
                        >
                            {loading ? (
                                <LoadingSpinner size="small" color="white" />
                            ) : (
                                <span className="flex items-center">
                                    Sign in to Trade123
                                </span>
                            )}
                        </motion.button>
                    </div>

                    {/* Additional Links */}
                    <div className="flex items-center justify-between">
                        <button
                            type="button"
                            className="text-sm text-primary-600 hover:text-primary-500 font-medium"
                        >
                            Forgot your password?
                        </button>

                        <button
                            type="button"
                            className="text-sm text-gray-600 hover:text-gray-500"
                        >
                            Need help?
                        </button>
                    </div>
                </motion.form>

                {/* Demo Credentials */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.6 }}
                    className="bg-gray-50 rounded-lg p-4 border border-gray-200"
                >
                    <h4 className="text-sm font-medium text-gray-900 mb-2">Demo Credentials</h4>
                    <div className="text-xs text-gray-600 space-y-1">
                        <p><strong>Email:</strong> demo@trade123.com</p>
                        <p><strong>Password:</strong> demo123</p>
                    </div>
                    <button
                        type="button"
                        onClick={() => {
                            setFormData({
                                email: 'demo@trade123.com',
                                password: 'demo123'
                            })
                        }}
                        className="mt-2 text-xs text-primary-600 hover:text-primary-700 font-medium"
                    >
                        Use demo credentials
                    </button>
                </motion.div>

                {/* Footer */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.7 }}
                    className="text-center"
                >
                    <p className="text-xs text-gray-500">
                        © 2025 Trade123. Advanced Trading Platform.
                    </p>
                </motion.div>
            </motion.div>
        </div>
    )
}

export default Login 