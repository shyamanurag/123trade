import { motion } from 'framer-motion'
import { BarChart3, PieChart, TrendingUp } from 'lucide-react'
import React from 'react'

const Analytics = () => {
    return (
        <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Analytics Dashboard</h1>
                    <p className="text-gray-600 mt-1">Comprehensive trading performance insights</p>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="card">
                    <div className="flex items-center space-x-3 mb-4">
                        <BarChart3 className="w-6 h-6 text-primary-600" />
                        <h3 className="text-lg font-semibold text-gray-900">Performance Chart</h3>
                    </div>
                    <div className="h-64 flex items-center justify-center bg-gray-50 rounded-lg">
                        <p className="text-gray-500">Performance Chart Component</p>
                    </div>
                </motion.div>

                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="card">
                    <div className="flex items-center space-x-3 mb-4">
                        <PieChart className="w-6 h-6 text-primary-600" />
                        <h3 className="text-lg font-semibold text-gray-900">Portfolio Distribution</h3>
                    </div>
                    <div className="h-64 flex items-center justify-center bg-gray-50 rounded-lg">
                        <p className="text-gray-500">Portfolio Pie Chart</p>
                    </div>
                </motion.div>

                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="card">
                    <div className="flex items-center space-x-3 mb-4">
                        <TrendingUp className="w-6 h-6 text-primary-600" />
                        <h3 className="text-lg font-semibold text-gray-900">Trend Analysis</h3>
                    </div>
                    <div className="h-64 flex items-center justify-center bg-gray-50 rounded-lg">
                        <p className="text-gray-500">Trend Analysis Chart</p>
                    </div>
                </motion.div>
            </div>
        </div>
    )
}

export default Analytics 