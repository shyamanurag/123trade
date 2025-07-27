import { motion } from 'framer-motion'
import {
    Activity,
    Clock,
    MoreVertical,
    ShoppingBag,
    ShoppingCart,
    TrendingDown,
    TrendingUp
} from 'lucide-react'
import React from 'react'

const RecentTradesWidget = ({ trades }) => {
    // Show empty state if no data provided
    if (!trades || trades.length === 0) {
        return (
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="card h-fit"
            >
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <h3 className="text-lg font-semibold text-gray-900 mb-1">
                            Recent Trades
                        </h3>
                        <p className="text-sm text-gray-600">
                            Waiting for trading data...
                        </p>
                    </div>
                    <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 rounded-lg bg-primary-100 flex items-center justify-center">
                            <Activity className="w-5 h-5 text-primary-600" />
                        </div>
                    </div>
                </div>
                <div className="text-center py-12">
                    <Activity className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                    <h4 className="text-lg font-semibold text-gray-900 mb-2">No Recent Trades</h4>
                    <p className="text-gray-600">Your recent trading activity will appear here</p>
                </div>
            </motion.div>
        )
    }

    const tradesData = trades

    const getStatusColor = (status) => {
        switch (status) {
            case 'COMPLETED':
                return 'text-success-600 bg-success-50'
            case 'PENDING':
                return 'text-warning-600 bg-warning-50'
            case 'FAILED':
                return 'text-danger-600 bg-danger-50'
            default:
                return 'text-gray-600 bg-gray-50'
        }
    }

    const getTimeAgo = (timestamp) => {
        const now = new Date()
        const time = new Date(timestamp)
        const diffInMinutes = Math.floor((now - time) / (1000 * 60))

        if (diffInMinutes < 1) return 'Just now'
        if (diffInMinutes < 60) return `${diffInMinutes}m ago`
        const diffInHours = Math.floor(diffInMinutes / 60)
        if (diffInHours < 24) return `${diffInHours}h ago`
        const diffInDays = Math.floor(diffInHours / 24)
        return `${diffInDays}d ago`
    }

    const containerVariants = {
        hidden: { opacity: 0 },
        visible: {
            opacity: 1,
            transition: {
                staggerChildren: 0.08
            }
        }
    }

    const itemVariants = {
        hidden: { opacity: 0, y: 20 },
        visible: {
            opacity: 1,
            y: 0,
            transition: {
                duration: 0.4
            }
        }
    }

    return (
        <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="card h-fit"
        >
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-1">
                        Recent Trades
                    </h3>
                    <p className="text-sm text-gray-600">
                        Latest trading activity
                    </p>
                </div>

                <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 rounded-lg bg-primary-100 flex items-center justify-center">
                        <Activity className="w-5 h-5 text-primary-600" />
                    </div>
                </div>
            </div>

            <div className="space-y-3">
                {tradesData.slice(0, 5).map((trade) => {
                    const isBuy = trade.type === 'BUY'
                    const isProfitable = trade.pnl > 0

                    return (
                        <motion.div
                            key={trade.id}
                            variants={itemVariants}
                            className="flex items-center justify-between p-3 rounded-lg border border-gray-200 hover:border-primary-300 hover:shadow-sm transition-all duration-200"
                            whileHover={{ scale: 1.02 }}
                        >
                            <div className="flex items-center space-x-3">
                                <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${isBuy ? 'bg-success-100 text-success-600' : 'bg-danger-100 text-danger-600'
                                    }`}>
                                    {isBuy ? (
                                        <ShoppingCart className="w-5 h-5" />
                                    ) : (
                                        <ShoppingBag className="w-5 h-5" />
                                    )}
                                </div>

                                <div>
                                    <div className="flex items-center space-x-2">
                                        <h4 className="font-semibold text-gray-900">
                                            {trade.symbol}
                                        </h4>
                                        <span className={`text-xs px-2 py-1 rounded-full font-medium ${getStatusColor(trade.status)}`}>
                                            {trade.status}
                                        </span>
                                    </div>
                                    <div className="flex items-center space-x-3 mt-1">
                                        <p className="text-sm text-gray-600">
                                            {trade.type} {trade.quantity} @ ₹{trade.price}
                                        </p>
                                        <div className="flex items-center space-x-1 text-gray-500">
                                            <Clock className="w-3 h-3" />
                                            <span className="text-xs">
                                                {getTimeAgo(trade.timestamp)}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div className="flex items-center space-x-3">
                                {trade.status === 'COMPLETED' && trade.pnl !== 0 && (
                                    <div className={`flex items-center space-x-1 ${isProfitable ? 'text-success-600' : 'text-danger-600'
                                        }`}>
                                        {isProfitable ? (
                                            <TrendingUp className="w-4 h-4" />
                                        ) : (
                                            <TrendingDown className="w-4 h-4" />
                                        )}
                                        <span className="text-sm font-semibold">
                                            ₹{Math.abs(trade.pnl).toLocaleString()}
                                        </span>
                                    </div>
                                )}

                                <button className="p-1 rounded-lg hover:bg-gray-100 transition-colors">
                                    <MoreVertical className="w-4 h-4 text-gray-500" />
                                </button>
                            </div>
                        </motion.div>
                    )
                })}
            </div>

            {tradesData.length === 0 && (
                <div className="text-center py-8">
                    <Activity className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                    <p className="text-gray-600">No recent trades</p>
                    <p className="text-sm text-gray-500 mt-1">
                        Your recent trading activity will appear here
                    </p>
                </div>
            )}

            <div className="mt-6 pt-4 border-t border-gray-200">
                <button className="w-full text-center text-sm text-primary-600 hover:text-primary-700 font-medium transition-colors">
                    View All Trades
                </button>
            </div>
        </motion.div>
    )
}

export default RecentTradesWidget 