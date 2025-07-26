import { motion } from 'framer-motion'
import {
    AlertCircle,
    CheckCircle,
    Clock,
    Download,
    Network,
    Plus,
    Send,
    Users
} from 'lucide-react'
import React, { useState } from 'react'
import toast from 'react-hot-toast'
import { useMutation, useQuery, useQueryClient } from 'react-query'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import { apiService } from '../services/apiService'

const MultiUserAPI = () => {
    const [showAPIForm, setShowAPIForm] = useState(false)
    const [apiData, setApiData] = useState({
        endpoint: '',
        method: 'GET',
        payload: '',
        headers: '{}',
        users: [],
        description: ''
    })

    const queryClient = useQueryClient()

    const { data: apiStatus, isLoading: statusLoading } = useQuery(
        'multi-user-api-status',
        apiService.getMultiUserAPIStatus,
        { refetchInterval: 10000 }
    )

    const { data: users } = useQuery(
        'users',
        () => apiService.getUsers({ active: true })
    )

    const submitAPIMutation = useMutation(
        apiService.submitMultiUserAPI,
        {
            onSuccess: () => {
                toast.success('API request submitted successfully!')
                queryClient.invalidateQueries('multi-user-api-status')
                setShowAPIForm(false)
                resetForm()
            },
            onError: (error) => {
                toast.error(error.message)
            }
        }
    )

    const resetForm = () => {
        setApiData({
            endpoint: '',
            method: 'GET',
            payload: '',
            headers: '{}',
            users: [],
            description: ''
        })
    }

    const handleSubmitAPI = (e) => {
        e.preventDefault()

        if (!apiData.endpoint.trim()) {
            toast.error('Please enter an API endpoint')
            return
        }

        if (apiData.users.length === 0) {
            toast.error('Please select at least one user')
            return
        }

        try {
            const parsedHeaders = JSON.parse(apiData.headers)
            const payload = apiData.payload ? JSON.parse(apiData.payload) : null

            submitAPIMutation.mutate({
                ...apiData,
                headers: parsedHeaders,
                payload
            })
        } catch (error) {
            toast.error('Invalid JSON in headers or payload')
        }
    }

    const getStatusColor = (status) => {
        switch (status) {
            case 'completed':
                return 'text-success-600 bg-success-100'
            case 'failed':
                return 'text-danger-600 bg-danger-100'
            case 'pending':
                return 'text-warning-600 bg-warning-100'
            case 'processing':
                return 'text-primary-600 bg-primary-100'
            default:
                return 'text-gray-600 bg-gray-100'
        }
    }

    const getStatusIcon = (status) => {
        switch (status) {
            case 'completed':
                return <CheckCircle className="w-4 h-4" />
            case 'failed':
                return <AlertCircle className="w-4 h-4" />
            case 'pending':
                return <Clock className="w-4 h-4" />
            case 'processing':
                return <LoadingSpinner size="small" />
            default:
                return <Network className="w-4 h-4" />
        }
    }

    if (statusLoading) {
        return (
            <div className="min-h-96 flex items-center justify-center">
                <LoadingSpinner size="large" text="Loading API status..." />
            </div>
        )
    }

    const requests = apiStatus?.recent_requests || []
    const stats = apiStatus?.statistics || {}

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Multi-User API Portal</h1>
                    <p className="text-gray-600 mt-1">
                        Submit API requests on behalf of multiple users
                    </p>
                </div>

                <button
                    onClick={() => setShowAPIForm(true)}
                    className="btn-primary flex items-center space-x-2 mt-4 sm:mt-0"
                >
                    <Plus className="w-4 h-4" />
                    <span>New API Request</span>
                </button>
            </div>

            {/* Statistics */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="metric-card"
                >
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm font-medium text-gray-600">Total Requests</p>
                            <p className="text-2xl font-bold text-gray-900">{stats.total_requests || 0}</p>
                        </div>
                        <div className="w-12 h-12 bg-primary-100 text-primary-600 rounded-lg flex items-center justify-center">
                            <Network className="w-6 h-6" />
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
                            <p className="text-sm font-medium text-gray-600">Successful</p>
                            <p className="text-2xl font-bold text-success-600">{stats.successful || 0}</p>
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
                            <p className="text-sm font-medium text-gray-600">Failed</p>
                            <p className="text-2xl font-bold text-danger-600">{stats.failed || 0}</p>
                        </div>
                        <div className="w-12 h-12 bg-danger-100 text-danger-600 rounded-lg flex items-center justify-center">
                            <AlertCircle className="w-6 h-6" />
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
                            <p className="text-sm font-medium text-gray-600">Active Users</p>
                            <p className="text-2xl font-bold text-primary-600">{stats.active_users || 0}</p>
                        </div>
                        <div className="w-12 h-12 bg-primary-100 text-primary-600 rounded-lg flex items-center justify-center">
                            <Users className="w-6 h-6" />
                        </div>
                    </div>
                </motion.div>
            </div>

            {/* Recent Requests */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="card"
            >
                <div className="flex items-center justify-between mb-6">
                    <h3 className="text-lg font-semibold text-gray-900">Recent API Requests</h3>
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
                                    Request
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Method
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Users
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Status
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Submitted
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Actions
                                </th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {requests.map((request, index) => (
                                <tr key={index} className="hover:bg-gray-50">
                                    <td className="px-6 py-4">
                                        <div>
                                            <div className="text-sm font-medium text-gray-900 truncate max-w-xs">
                                                {request.endpoint}
                                            </div>
                                            {request.description && (
                                                <div className="text-sm text-gray-500 truncate max-w-xs">
                                                    {request.description}
                                                </div>
                                            )}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${request.method === 'GET' ? 'bg-primary-100 text-primary-800' :
                                                request.method === 'POST' ? 'bg-success-100 text-success-800' :
                                                    request.method === 'PUT' ? 'bg-warning-100 text-warning-800' :
                                                        'bg-danger-100 text-danger-800'
                                            }`}>
                                            {request.method}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                        {request.user_count || 0} users
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(request.status)
                                            }`}>
                                            {getStatusIcon(request.status)}
                                            <span className="ml-1 capitalize">{request.status}</span>
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                        {request.created_at
                                            ? new Date(request.created_at).toLocaleString()
                                            : 'N/A'
                                        }
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                        <button className="text-primary-600 hover:text-primary-900">
                                            View Details
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                {requests.length === 0 && (
                    <div className="text-center py-12">
                        <Network className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                        <h3 className="text-lg font-medium text-gray-900 mb-2">No API requests yet</h3>
                        <p className="text-gray-600">Start by submitting your first multi-user API request</p>
                    </div>
                )}
            </motion.div>

            {/* API Submission Form Modal */}
            {showAPIForm && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
                >
                    <motion.div
                        initial={{ scale: 0.95, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        className="bg-white rounded-xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto"
                    >
                        <h3 className="text-lg font-semibold text-gray-900 mb-4">Submit Multi-User API Request</h3>

                        <form onSubmit={handleSubmitAPI} className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        API Endpoint
                                    </label>
                                    <input
                                        type="text"
                                        value={apiData.endpoint}
                                        onChange={(e) => setApiData(prev => ({ ...prev, endpoint: e.target.value }))}
                                        placeholder="/api/v1/trades"
                                        className="input-field"
                                        required
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        HTTP Method
                                    </label>
                                    <select
                                        value={apiData.method}
                                        onChange={(e) => setApiData(prev => ({ ...prev, method: e.target.value }))}
                                        className="input-field"
                                    >
                                        <option value="GET">GET</option>
                                        <option value="POST">POST</option>
                                        <option value="PUT">PUT</option>
                                        <option value="DELETE">DELETE</option>
                                    </select>
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Description
                                </label>
                                <input
                                    type="text"
                                    value={apiData.description}
                                    onChange={(e) => setApiData(prev => ({ ...prev, description: e.target.value }))}
                                    placeholder="Brief description of this API request"
                                    className="input-field"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Select Users
                                </label>
                                <div className="max-h-40 overflow-y-auto border border-gray-300 rounded-lg p-3 space-y-2">
                                    {users?.data?.map((user) => (
                                        <label key={user.id} className="flex items-center space-x-2">
                                            <input
                                                type="checkbox"
                                                checked={apiData.users.includes(user.id)}
                                                onChange={(e) => {
                                                    if (e.target.checked) {
                                                        setApiData(prev => ({
                                                            ...prev,
                                                            users: [...prev.users, user.id]
                                                        }))
                                                    } else {
                                                        setApiData(prev => ({
                                                            ...prev,
                                                            users: prev.users.filter(id => id !== user.id)
                                                        }))
                                                    }
                                                }}
                                                className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                                            />
                                            <span className="text-sm text-gray-900">
                                                {user.name} ({user.email})
                                            </span>
                                        </label>
                                    ))}
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Headers (JSON)
                                </label>
                                <textarea
                                    value={apiData.headers}
                                    onChange={(e) => setApiData(prev => ({ ...prev, headers: e.target.value }))}
                                    placeholder='{"Content-Type": "application/json"}'
                                    className="input-field h-20 font-mono text-sm"
                                />
                            </div>

                            {(apiData.method === 'POST' || apiData.method === 'PUT') && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Request Payload (JSON)
                                    </label>
                                    <textarea
                                        value={apiData.payload}
                                        onChange={(e) => setApiData(prev => ({ ...prev, payload: e.target.value }))}
                                        placeholder='{"key": "value"}'
                                        className="input-field h-24 font-mono text-sm"
                                    />
                                </div>
                            )}

                            <div className="flex justify-end space-x-3 pt-4">
                                <button
                                    type="button"
                                    onClick={() => setShowAPIForm(false)}
                                    className="btn-secondary"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={submitAPIMutation.isLoading}
                                    className="btn-primary flex items-center space-x-2"
                                >
                                    {submitAPIMutation.isLoading ? (
                                        <LoadingSpinner size="small" color="white" />
                                    ) : (
                                        <Send className="w-4 h-4" />
                                    )}
                                    <span>Submit Request</span>
                                </button>
                            </div>
                        </form>
                    </motion.div>
                </motion.div>
            )}
        </div>
    )
}

export default MultiUserAPI 