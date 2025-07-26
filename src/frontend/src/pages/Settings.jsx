import { motion } from 'framer-motion'
import { RefreshCw, Save, Settings as SettingsIcon } from 'lucide-react'
import React from 'react'

const Settings = () => {
    return (
        <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">System Settings</h1>
                    <p className="text-gray-600 mt-1">Configure trading platform preferences and parameters</p>
                </div>
                <button className="btn-primary flex items-center space-x-2 mt-4 sm:mt-0">
                    <Save className="w-4 h-4" />
                    <span>Save Changes</span>
                </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="card">
                    <div className="flex items-center space-x-3 mb-4">
                        <SettingsIcon className="w-6 h-6 text-primary-600" />
                        <h3 className="text-lg font-semibold text-gray-900">Trading Parameters</h3>
                    </div>
                    <div className="h-48 flex items-center justify-center bg-gray-50 rounded-lg">
                        <p className="text-gray-500">Trading Settings Form</p>
                    </div>
                </motion.div>

                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="card">
                    <div className="flex items-center space-x-3 mb-4">
                        <RefreshCw className="w-6 h-6 text-primary-600" />
                        <h3 className="text-lg font-semibold text-gray-900">System Configuration</h3>
                    </div>
                    <div className="h-48 flex items-center justify-center bg-gray-50 rounded-lg">
                        <p className="text-gray-500">System Config Panel</p>
                    </div>
                </motion.div>
            </div>
        </div>
    )
}

export default Settings 