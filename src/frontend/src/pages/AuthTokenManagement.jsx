import { motion } from 'framer-motion'
import {
    AlertCircle,
    CheckCircle,
    Clock,
    Download,
    Key,
    Plus,
    RefreshCw,
    Upload,
    Users
} from 'lucide-react'
import React, { useState } from 'react'
import toast from 'react-hot-toast'
import { useMutation, useQuery, useQueryClient } from 'react-query'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import { apiService } from '../services/apiService'
import { authService } from '../services/authService'

const AuthTokenManagement = () => {
    const [showTokenForm, setShowTokenForm] = useState(false)
    const [tokenData, setTokenData] = useState({
        token: '',
        expiresAt: '',
        userId: '',
        brokerType: 'zerodha'
    })

    const queryClient = useQueryClient()

    const { data: tokenStatus, isLoading: statusLoading } = useQuery(
        'token-status',
        apiService.getTokenStatus,
        { refetchInterval: 30000 }
    )

    const { data: allUserTokens, isLoading: tokensLoading } = useQuery(
        'all-user-tokens',
        apiService.getAllUserTokens,
        { refetchInterval: 60000 }
    )

    const submitTokenMutation = useMutation(
        apiService.submitDailyToken,
        {
            onSuccess: () => {
                toast.success('Token submitted successfully!')
                queryClient.invalidateQueries('token-status')
                queryClient.invalidateQueries('all-user-tokens')
                setShowTokenForm(false)
                setTokenData({
                    token: '',
                    expiresAt: '',
                    userId: '',
                    brokerType: 'zerodha'
                })
            },
            onError: (error) => {
                toast.error(error.message)
            }
        }
    )

    const refreshZerodhaTokenMutation = useMutation(
        authService.refreshZerodhaToken,
        {
            onSuccess: () => {
                toast.success('Zerodha token refreshed successfully!')
                queryClient.invalidateQueries('token-status')
            },
            onError: (error) => {
                toast.error(error.message)
            }
        }
    )

    const handleSubmitToken = (e) => {
        e.preventDefault()
        if (!tokenData.token.trim()) {
            toast.error('Please enter a token')
            return
        }
        submitTokenMutation.mutate(tokenData)
    }

    const getStatusColor = (status) => {
        switch (status) {
            case 'active':
                return 'text-success-600 bg-success-100'
            case 'expired':
                return 'text-danger-600 bg-danger-100'
            case 'expiring':
                return 'text-warning-600 bg-warning-100'
            default:
                return 'text-gray-600 bg-gray-100'
        }
    }

    const getStatusIcon = (status) => {
        switch (status) {
            case 'active':
                return <CheckCircle className="w-4 h-4" />
            case 'expired':
                return <AlertCircle className="w-4 h-4" />
            case 'expiring':
                return <Clock className="w-4 h-4" />
            default:
                return <Key className="w-4 h-4" />
        }
    }

    if (statusLoading || tokensLoading) {
        return (
            <div className="min-h-96 flex items-center justify-center">
                <LoadingSpinner size="large" text="Loading token information..." />
            </div>
        )
    }

    const tokens = allUserTokens || []
    const activeTokens = tokens.filter(t => t.status === 'active').length
    const expiringTokens = tokens.filter(t => t.status === 'expiring').length
    const expiredTokens = tokens.filter(t => t.status === 'expired').length

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Auth Token Management</h1>
                    <p className="text-gray-600 mt-1">
                        Manage daily authentication tokens for all users
                    </p>
                </div>

                <div className="flex items-center space-x-3 mt-4 sm:mt-0">
                    <button
                        onClick={() => refreshZerodhaTokenMutation.mutate()}
                        disabled={refreshZerodhaTokenMutation.isLoading}
                        className="btn-secondary flex items-center space-x-2"
                    >
                        <RefreshCw className={`w-4 h-4 ${refreshZerodhaTokenMutation.isLoading ? 'animate-spin' : ''}`} />
                        <span>Refresh Zerodha</span>
                    </button>

                    <button
                        onClick={() => setShowTokenForm(true)}
                        className="btn-primary flex items-center space-x-2"
                    >
                        <Plus className="w-4 h-4" />
                        <span>Add Token</span>
                    </button>
                </div>
            </div>

            {/* Statistics Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="metric-card"
                >
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm font-medium text-gray-600">Total Users</p>
                            <p className="text-2xl font-bold text-gray-900">{tokens.length}</p>
                        </div>
                        <div className="w-12 h-12 bg-primary-100 text-primary-600 rounded-lg flex items-center justify-center">
                            <Users className="w-6 h-6" />
                        </div>
                    </div>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="metric-card"
                >
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm font-medium text-gray-600">Active Tokens</p>
                            <p className="text-2xl font-bold text-success-600">{activeTokens}</p>
                        </div>
                        <div className="w-12 h-12 bg-success-100 text-success-600 rounded-lg flex items-center justify-center">
                            <CheckCircle className="w-6 h-6" />
                        </div>
                    </div>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="metric-card"
                >
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm font-medium text-gray-600">Expiring Soon</p>
                            <p className="text-2xl font-bold text-warning-600">{expiringTokens}</p>
                        </div>
                        <div className="w-12 h-12 bg-warning-100 text-warning-600 rounded-lg flex items-center justify-center">
                            <Clock className="w-6 h-6" />
                        </div>
                    </div>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                    className="metric-card"
                >
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm font-medium text-gray-600">Expired</p>
                            <p className="text-2xl font-bold text-danger-600">{expiredTokens}</p>
                        </div>
                        <div className="w-12 h-12 bg-danger-100 text-danger-600 rounded-lg flex items-center justify-center">
                            <AlertCircle className="w-6 h-6" />
                        </div>
                    </div>
                </motion.div>
            </div>

            {/* Current Status */}
            {tokenStatus && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="card"
                >
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">Current Token Status</h3>

                    <div className="space-y-4">
                        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                            <div className="flex items-center space-x-3">
                                <div className={`p-2 rounded-lg ${getStatusColor(tokenStatus.zerodha_status)}`}>
                                    {getStatusIcon(tokenStatus.zerodha_status)}
                                </div>
                                <div>
                                    <p className="font-medium text-gray-900">Zerodha Token</p>
                                    <p className="text-sm text-gray-600">
                                        {tokenStatus.zerodha_expires_at
                                            ? `Expires: ${new Date(tokenStatus.zerodha_expires_at).toLocaleString()}`
                                            : 'No expiry information'
                                        }
                                    </p>
                                </div>
                            </div>

                            <div className="text-right">
                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(tokenStatus.zerodha_status)
                                    }`}>
                                    {tokenStatus.zerodha_status}
                                </span>
                            </div>
                        </div>
                    </div>
                </motion.div>
            )}

            {/* User Tokens Table */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="card"
            >
                <div className="flex items-center justify-between mb-6">
                    <h3 className="text-lg font-semibold text-gray-900">All User Tokens</h3>
                    <div className="flex items-center space-x-2">
                        <button className="btn-secondary flex items-center space-x-2">
                            <Download className="w-4 h-4" />
                            <span>Export</span>
                        </button>
                    </div>
                </div>

                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    User
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Broker
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Status
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Expires At
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Last Updated
                                </th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {tokens.map((token, index) => (
                                <tr key={index} className="hover:bg-gray-50">
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="flex items-center">
                                            <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center">
                                                <span className="text-primary-600 font-medium text-sm">
                                                    {token.username?.charAt(0) || 'U'}
                                                </span>
                                            </div>
                                            <div className="ml-4">
                                                <div className="text-sm font-medium text-gray-900">
                                                    {token.username || 'Unknown User'}
                                                </div>
                                                <div className="text-sm text-gray-500">
                                                    {token.email || 'No email'}
                                                </div>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className="text-sm text-gray-900 capitalize">
                                            {token.broker_type || 'Unknown'}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(token.status)
                                            }`}>
                                            {getStatusIcon(token.status)}
                                            <span className="ml-1 capitalize">{token.status}</span>
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                        {token.expires_at
                                            ? new Date(token.expires_at).toLocaleString()
                                            : 'N/A'
                                        }
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                        {token.updated_at
                                            ? new Date(token.updated_at).toLocaleString()
                                            : 'N/A'
                                        }
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                {tokens.length === 0 && (
                    <div className="text-center py-12">
                        <Key className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                        <h3 className="text-lg font-medium text-gray-900 mb-2">No tokens found</h3>
                        <p className="text-gray-600">Start by adding a daily token for users</p>
                    </div>
                )}
            </motion.div>

            {/* Token Submission Form Modal */}
            {showTokenForm && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
                >
                    <motion.div
                        initial={{ scale: 0.95, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        className="bg-white rounded-xl p-6 w-full max-w-md"
                    >
                        <h3 className="text-lg font-semibold text-gray-900 mb-4">Submit Daily Token</h3>

                        <form onSubmit={handleSubmitToken} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Broker Type
                                </label>
                                <select
                                    value={tokenData.brokerType}
                                    onChange={(e) => setTokenData(prev => ({ ...prev, brokerType: e.target.value }))}
                                    className="input-field"
                                >
                                    <option value="zerodha">Zerodha</option>
                                    <option value="sharekhan">Sharekhan</option>
                                    <option value="truedata">TrueData</option>
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Authentication Token
                                </label>
                                <textarea
                                    value={tokenData.token}
                                    onChange={(e) => setTokenData(prev => ({ ...prev, token: e.target.value }))}
                                    placeholder="Paste your daily authentication token here..."
                                    className="input-field h-24 resize-none"
                                    required
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    User ID (Optional)
                                </label>
                                <input
                                    type="text"
                                    value={tokenData.userId}
                                    onChange={(e) => setTokenData(prev => ({ ...prev, userId: e.target.value }))}
                                    placeholder="Leave empty for current user"
                                    className="input-field"
                                />
                            </div>

                            <div className="flex justify-end space-x-3 pt-4">
                                <button
                                    type="button"
                                    onClick={() => setShowTokenForm(false)}
                                    className="btn-secondary"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={submitTokenMutation.isLoading}
                                    className="btn-primary flex items-center space-x-2"
                                >
                                    {submitTokenMutation.isLoading ? (
                                        <LoadingSpinner size="small" color="white" />
                                    ) : (
                                        <Upload className="w-4 h-4" />
                                    )}
                                    <span>Submit Token</span>
                                </button>
                            </div>
                        </form>
                    </motion.div>
                </motion.div>
            )}
        </div>
    )
}

export default AuthTokenManagement 