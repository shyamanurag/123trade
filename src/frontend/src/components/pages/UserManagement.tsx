import { CheckCircleIcon, PencilIcon, PlusIcon, TrashIcon, UsersIcon, XCircleIcon } from '@heroicons/react/24/outline';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { useState } from 'react';
import toast from 'react-hot-toast';

interface User {
    id: string;
    username: string;
    email: string;
    sharekhan_user_id?: string;
    status: 'active' | 'inactive' | 'suspended';
    created_at: string;
    last_login?: string;
    total_trades?: number;
    current_pnl?: number;
}

interface CreateUserRequest {
    username: string;
    email: string;
    password: string;
    sharekhan_user_id?: string;
}

export default function UserManagement() {
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [editingUser, setEditingUser] = useState<User | null>(null);
    const [newUser, setNewUser] = useState<CreateUserRequest>({
        username: '',
        email: '',
        password: '',
        sharekhan_user_id: ''
    });
    const queryClient = useQueryClient();

    // Fetch all users
    const { data: users, isLoading, error } = useQuery<User[]>({
        queryKey: ['users'],
        queryFn: async () => {
            const response = await axios.get('/api/users');
            if (!response.data.success) {
                throw new Error('Failed to fetch users');
            }
            return response.data.data;
        },
        refetchInterval: 30000,
    });

    // Create user mutation
    const createUserMutation = useMutation({
        mutationFn: async (userData: CreateUserRequest) => {
            const response = await axios.post('/api/users', userData);
            if (!response.data.success) {
                throw new Error('Failed to create user');
            }
            return response.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['users'] });
            setShowCreateModal(false);
            setNewUser({ username: '', email: '', password: '', sharekhan_user_id: '' });
            toast.success('User created successfully');
        },
        onError: (error: any) => {
            toast.error(`Failed to create user: ${error.message}`);
        },
    });

    // Update user mutation
    const updateUserMutation = useMutation({
        mutationFn: async ({ id, updates }: { id: string; updates: Partial<User> }) => {
            const response = await axios.put(`/api/users/${id}`, updates);
            if (!response.data.success) {
                throw new Error('Failed to update user');
            }
            return response.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['users'] });
            setEditingUser(null);
            toast.success('User updated successfully');
        },
        onError: (error: any) => {
            toast.error(`Failed to update user: ${error.message}`);
        },
    });

    // Delete user mutation
    const deleteUserMutation = useMutation({
        mutationFn: async (userId: string) => {
            const response = await axios.delete(`/api/users/${userId}`);
            if (!response.data.success) {
                throw new Error('Failed to delete user');
            }
            return response.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['users'] });
            toast.success('User deleted successfully');
        },
        onError: (error: any) => {
            toast.error(`Failed to delete user: ${error.message}`);
        },
    });

    // Toggle user status
    const toggleUserStatus = (user: User) => {
        const newStatus = user.status === 'active' ? 'inactive' : 'active';
        updateUserMutation.mutate({
            id: user.id,
            updates: { status: newStatus }
        });
    };

    const handleCreateUser = () => {
        if (!newUser.username || !newUser.email || !newUser.password) {
            toast.error('Please fill in all required fields');
            return;
        }
        createUserMutation.mutate(newUser);
    };

    const formatCurrency = (value?: number) => {
        if (!value) return '₹0.00';
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
        }).format(value);
    };

    if (error) {
        return (
            <div className="bg-red-50 border border-red-200 rounded-lg p-6">
                <h2 className="text-red-800 font-medium">Database Connection Error</h2>
                <p className="text-red-600 text-sm mt-1">Cannot connect to user database. Check system configuration.</p>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">User Management</h1>
                    <p className="mt-1 text-sm text-gray-600">
                        Manage ShareKhan trading system users - Real database users only
                    </p>
                </div>
                <button
                    onClick={() => setShowCreateModal(true)}
                    className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                    <PlusIcon className="h-4 w-4 mr-2" />
                    Add New User
                </button>
            </div>

            {/* Users Table */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200">
                    <h2 className="text-lg font-medium text-gray-900">System Users</h2>
                </div>

                {isLoading ? (
                    <div className="p-6 text-center">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                        <p className="mt-2 text-gray-600">Loading users...</p>
                    </div>
                ) : users && users.length > 0 ? (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">User</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ShareKhan ID</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Trades</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Current P&L</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Last Login</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {users.map((user) => (
                                    <tr key={user.id}>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex items-center">
                                                <UsersIcon className="h-5 w-5 text-gray-400 mr-3" />
                                                <div>
                                                    <div className="text-sm font-medium text-gray-900">{user.username}</div>
                                                    <div className="text-sm text-gray-500">{user.email}</div>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                            {user.sharekhan_user_id || 'Not set'}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex items-center">
                                                {user.status === 'active' ? (
                                                    <CheckCircleIcon className="h-5 w-5 text-green-500 mr-2" />
                                                ) : (
                                                    <XCircleIcon className="h-5 w-5 text-red-500 mr-2" />
                                                )}
                                                <span className={`text-sm font-medium capitalize ${user.status === 'active' ? 'text-green-700' : 'text-red-700'
                                                    }`}>
                                                    {user.status}
                                                </span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                            {user.total_trades || 0}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                                            <span className={`font-medium ${(user.current_pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                                                }`}>
                                                {formatCurrency(user.current_pnl)}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                            {user.last_login ? new Date(user.last_login).toLocaleString() : 'Never'}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                                            <button
                                                onClick={() => setEditingUser(user)}
                                                className="text-blue-600 hover:text-blue-900"
                                            >
                                                <PencilIcon className="h-4 w-4" />
                                            </button>
                                            <button
                                                onClick={() => toggleUserStatus(user)}
                                                className={`${user.status === 'active' ? 'text-red-600 hover:text-red-900' : 'text-green-600 hover:text-green-900'
                                                    }`}
                                            >
                                                {user.status === 'active' ? 'Suspend' : 'Activate'}
                                            </button>
                                            <button
                                                onClick={() => {
                                                    if (window.confirm('Are you sure you want to delete this user?')) {
                                                        deleteUserMutation.mutate(user.id);
                                                    }
                                                }}
                                                className="text-red-600 hover:text-red-900"
                                            >
                                                <TrashIcon className="h-4 w-4" />
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <div className="p-6 text-center text-gray-500">
                        No users found in the system
                    </div>
                )}
            </div>

            {/* Create User Modal */}
            {showCreateModal && (
                <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
                    <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
                        <div className="mt-3">
                            <h3 className="text-lg font-medium text-gray-900 mb-4">Create New User</h3>
                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700">Username *</label>
                                    <input
                                        type="text"
                                        value={newUser.username}
                                        onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                                        className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700">Email *</label>
                                    <input
                                        type="email"
                                        value={newUser.email}
                                        onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                                        className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700">Password *</label>
                                    <input
                                        type="password"
                                        value={newUser.password}
                                        onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                                        className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700">ShareKhan User ID</label>
                                    <input
                                        type="text"
                                        value={newUser.sharekhan_user_id}
                                        onChange={(e) => setNewUser({ ...newUser, sharekhan_user_id: e.target.value })}
                                        className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                                    />
                                </div>
                            </div>
                            <div className="flex justify-between mt-6">
                                <button
                                    onClick={handleCreateUser}
                                    disabled={createUserMutation.isLoading}
                                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                                >
                                    {createUserMutation.isLoading ? 'Creating...' : 'Create User'}
                                </button>
                                <button
                                    onClick={() => setShowCreateModal(false)}
                                    className="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400"
                                >
                                    Cancel
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
} 