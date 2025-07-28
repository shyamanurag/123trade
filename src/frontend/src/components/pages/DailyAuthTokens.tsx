import { ArrowPathIcon, CheckCircleIcon, ClockIcon, KeyIcon, XCircleIcon } from '@heroicons/react/24/outline';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { useState } from 'react';
import toast from 'react-hot-toast';

interface AuthToken {
    user_id: string;
    username: string;
    token: string;
    token_type: string;
    expires_at: string;
    status: 'active' | 'expired' | 'pending';
    last_used: string;
    auth_url?: string;
}

interface User {
    id: string;
    username: string;
    email: string;
    sharekhan_user_id?: string;
    status: string;
}

export default function DailyAuthTokens() {
    const [selectedUser, setSelectedUser] = useState<string>('');
    const [showAuthModal, setShowAuthModal] = useState(false);
    const [authUrl, setAuthUrl] = useState('');
    const queryClient = useQueryClient();

    // Fetch all users
    const { data: users } = useQuery<User[]>({
        queryKey: ['users'],
        queryFn: async () => {
            const response = await axios.get('/api/users');
            return response.data.data;
        },
    });

    // Fetch auth tokens
    const { data: tokens, isLoading } = useQuery<AuthToken[]>({
        queryKey: ['auth-tokens'],
        queryFn: async () => {
            const response = await axios.get('/api/auth/tokens');
            return response.data.data;
        },
        refetchInterval: 30000, // Refresh every 30 seconds
    });

    // Generate auth URL mutation
    const generateAuthUrl = useMutation({
        mutationFn: async (userId: string) => {
            const response = await axios.post('/api/sharekhan/auth/generate-url', {
                user_id: userId
            });
            return response.data;
        },
        onSuccess: (data) => {
            setAuthUrl(data.auth_url);
            setShowAuthModal(true);
            toast.success('Auth URL generated successfully');
        },
        onError: () => {
            toast.error('Failed to generate auth URL');
        },
    });

    // Refresh token mutation
    const refreshToken = useMutation({
        mutationFn: async (userId: string) => {
            const response = await axios.post('/api/sharekhan/auth/refresh', {
                user_id: userId
            });
            return response.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['auth-tokens'] });
            toast.success('Token refreshed successfully');
        },
        onError: () => {
            toast.error('Failed to refresh token');
        },
    });

    // Revoke token mutation
    const revokeToken = useMutation({
        mutationFn: async (userId: string) => {
            const response = await axios.post('/api/sharekhan/auth/revoke', {
                user_id: userId
            });
            return response.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['auth-tokens'] });
            toast.success('Token revoked successfully');
        },
        onError: () => {
            toast.error('Failed to revoke token');
        },
    });

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'active':
                return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
            case 'expired':
                return <XCircleIcon className="h-5 w-5 text-red-500" />;
            case 'pending':
                return <ClockIcon className="h-5 w-5 text-yellow-500" />;
            default:
                return <XCircleIcon className="h-5 w-5 text-gray-500" />;
        }
    };

    const formatTimeRemaining = (expiresAt: string) => {
        const now = new Date();
        const expiry = new Date(expiresAt);
        const diff = expiry.getTime() - now.getTime();

        if (diff <= 0) return 'Expired';

        const hours = Math.floor(diff / (1000 * 60 * 60));
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

        return `${hours}h ${minutes}m`;
    };

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">Daily Auth Tokens</h1>
                    <p className="mt-1 text-sm text-gray-600">
                        Manage ShareKhan daily authentication tokens for all users
                    </p>
                </div>

                <button
                    onClick={() => queryClient.invalidateQueries({ queryKey: ['auth-tokens'] })}
                    className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                    <ArrowPathIcon className="h-4 w-4 mr-2" />
                    Refresh
                </button>
            </div>

            {/* Add New Token */}
            <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-medium text-gray-900 mb-4">Generate New Auth Token</h2>
                <div className="flex space-x-4">
                    <select
                        value={selectedUser}
                        onChange={(e) => setSelectedUser(e.target.value)}
                        className="flex-1 border border-gray-300 rounded-md px-3 py-2"
                    >
                        <option value="">Select User</option>
                        {users?.map((user) => (
                            <option key={user.id} value={user.id}>
                                {user.username} ({user.email})
                            </option>
                        ))}
                    </select>
                    <button
                        onClick={() => selectedUser && generateAuthUrl.mutate(selectedUser)}
                        disabled={!selectedUser || generateAuthUrl.isLoading}
                        className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                    >
                        {generateAuthUrl.isLoading ? 'Generating...' : 'Generate Auth URL'}
                    </button>
                </div>
            </div>

            {/* Tokens Table */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200">
                    <h2 className="text-lg font-medium text-gray-900">Active Tokens</h2>
                </div>

                {isLoading ? (
                    <div className="p-6 text-center">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                        <p className="mt-2 text-gray-600">Loading tokens...</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        User
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Status
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Token Type
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Expires In
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Last Used
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Actions
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {tokens?.map((token) => (
                                    <tr key={token.user_id}>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex items-center">
                                                <KeyIcon className="h-5 w-5 text-gray-400 mr-3" />
                                                <div>
                                                    <div className="text-sm font-medium text-gray-900">{token.username}</div>
                                                    <div className="text-sm text-gray-500">{token.user_id}</div>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex items-center">
                                                {getStatusIcon(token.status)}
                                                <span className={`ml-2 text-sm font-medium capitalize ${token.status === 'active' ? 'text-green-700' :
                                                    token.status === 'expired' ? 'text-red-700' :
                                                        'text-yellow-700'
                                                    }`}>
                                                    {token.status}
                                                </span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                            {token.token_type}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                            {formatTimeRemaining(token.expires_at)}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                            {token.last_used ? new Date(token.last_used).toLocaleString() : 'Never'}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                                            <button
                                                onClick={() => refreshToken.mutate(token.user_id)}
                                                className="text-blue-600 hover:text-blue-900"
                                            >
                                                Refresh
                                            </button>
                                            <button
                                                onClick={() => revokeToken.mutate(token.user_id)}
                                                className="text-red-600 hover:text-red-900"
                                            >
                                                Revoke
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Auth URL Modal */}
            {showAuthModal && (
                <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
                    <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
                        <div className="mt-3">
                            <h3 className="text-lg font-medium text-gray-900 mb-4">ShareKhan Auth URL</h3>
                            <p className="text-sm text-gray-600 mb-4">
                                Open this URL in a new tab to complete ShareKhan authentication:
                            </p>
                            <div className="bg-gray-100 p-3 rounded border text-sm break-all">
                                {authUrl}
                            </div>
                            <div className="flex justify-between mt-6">
                                <button
                                    onClick={() => window.open(authUrl, '_blank')}
                                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                                >
                                    Open URL
                                </button>
                                <button
                                    onClick={() => setShowAuthModal(false)}
                                    className="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400"
                                >
                                    Close
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
} 