import { motion } from 'framer-motion'
import { Plus, Search, Users as UsersIcon } from 'lucide-react'
import React from 'react'

const Users = () => {
    return (
        <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">User Management</h1>
                    <p className="text-gray-600 mt-1">Manage trading platform users and permissions</p>
                </div>
                <button className="btn-primary flex items-center space-x-2 mt-4 sm:mt-0">
                    <Plus className="w-4 h-4" />
                    <span>Add User</span>
                </button>
            </div>

            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="card">
                <div className="flex items-center space-x-3 mb-6">
                    <UsersIcon className="w-6 h-6 text-primary-600" />
                    <h3 className="text-lg font-semibold text-gray-900">User Directory</h3>
                </div>

                <div className="mb-4">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                        <input
                            type="text"
                            placeholder="Search users..."
                            className="input-field pl-10"
                        />
                    </div>
                </div>

                <div className="h-64 flex items-center justify-center bg-gray-50 rounded-lg">
                    <div className="text-center">
                        <UsersIcon className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                        <p className="text-gray-500">User Management Interface</p>
                        <p className="text-sm text-gray-400 mt-1">Add, edit, and manage trading platform users</p>
                    </div>
                </div>
            </motion.div>
        </div>
    )
}

export default Users 