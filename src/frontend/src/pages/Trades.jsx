import { motion } from 'framer-motion'
import { DollarSign, Download, Filter } from 'lucide-react'
import React from 'react'

const Trades = () => {
    return (
        <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Trade History</h1>
                    <p className="text-gray-600 mt-1">View and analyze all trading activity</p>
                </div>
                <div className="flex items-center space-x-3 mt-4 sm:mt-0">
                    <button className="btn-secondary flex items-center space-x-2">
                        <Filter className="w-4 h-4" />
                        <span>Filter</span>
                    </button>
                    <button className="btn-primary flex items-center space-x-2">
                        <Download className="w-4 h-4" />
                        <span>Export</span>
                    </button>
                </div>
            </div>

            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="card">
                <div className="flex items-center space-x-3 mb-6">
                    <DollarSign className="w-6 h-6 text-primary-600" />
                    <h3 className="text-lg font-semibold text-gray-900">Recent Trades</h3>
                </div>

                <div className="h-96 flex items-center justify-center bg-gray-50 rounded-lg">
                    <div className="text-center">
                        <DollarSign className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                        <p className="text-gray-500">Trade History Table</p>
                        <p className="text-sm text-gray-400 mt-1">View detailed trade information, P&L, and analytics</p>
                    </div>
                </div>
            </motion.div>
        </div>
    )
}

export default Trades 