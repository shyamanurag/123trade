import { motion } from 'framer-motion'
import { Activity, BarChart3, TrendingDown, TrendingUp } from 'lucide-react'
import React from 'react'

const LiveIndicesWidget = ({ indices }) => {
    // Show empty state if no data provided
    if (!indices || indices.length === 0) {
        return (
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="card"
            >
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <h3 className="text-lg font-semibold text-gray-900 mb-1">
                            Live Market Indices
                        </h3>
                        <p className="text-sm text-gray-600">
                            Waiting for market data...
                        </p>
                    </div>
                    <div className="flex items-center space-x-3">
                        <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
                        <span className="text-sm text-gray-600">Connecting...</span>
                        <div className="w-10 h-10 rounded-lg bg-primary-100 flex items-center justify-center">
                            <BarChart3 className="w-5 h-5 text-primary-600" />
                        </div>
                    </div>
                </div>
                <div className="text-center py-12">
                    <BarChart3 className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                    <h4 className="text-lg font-semibold text-gray-900 mb-2">No Market Data</h4>
                    <p className="text-gray-600">Live indices will appear when market feed is connected</p>
                </div>
            </motion.div>
        )
    }

    const indicesData = indices

    const containerVariants = {
        hidden: { opacity: 0 },
        visible: {
            opacity: 1,
            transition: {
                staggerChildren: 0.1
            }
        }
    }

    const itemVariants = {
        hidden: { opacity: 0, x: -20 },
        visible: {
            opacity: 1,
            x: 0,
            transition: {
                duration: 0.5
            }
        }
    }

    return (
        <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="card"
        >
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-1">
                        Live Market Indices
                    </h3>
                    <p className="text-sm text-gray-600">
                        Real-time market data
                    </p>
                </div>

                <div className="flex items-center space-x-3">
                    <div className="w-2 h-2 bg-success-500 rounded-full animate-pulse"></div>
                    <span className="text-sm text-gray-600">Live</span>
                    <div className="w-10 h-10 rounded-lg bg-primary-100 flex items-center justify-center">
                        <BarChart3 className="w-5 h-5 text-primary-600" />
                    </div>
                </div>
            </div>

            <div className="space-y-4">
                {indicesData.map((index, idx) => {
                    const isPositive = index.change >= 0

                    return (
                        <motion.div
                            key={index.symbol}
                            variants={itemVariants}
                            className="flex items-center justify-between p-4 rounded-lg border border-gray-200 hover:border-primary-300 hover:shadow-sm transition-all duration-200"
                            whileHover={{ scale: 1.01 }}
                        >
                            <div className="flex-1">
                                <div className="flex items-center space-x-3">
                                    <div>
                                        <h4 className="font-semibold text-gray-900">
                                            {index.name}
                                        </h4>
                                        <p className="text-sm text-gray-500">
                                            {index.symbol}
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <div className="flex items-center space-x-6">
                                <div className="text-right">
                                    <p className="text-lg font-bold text-gray-900">
                                        {index.value.toLocaleString()}
                                    </p>
                                    <p className="text-xs text-gray-500">
                                        {new Date(index.lastUpdate).toLocaleTimeString()}
                                    </p>
                                </div>

                                <div className={`flex items-center space-x-1 min-w-[100px] justify-end ${isPositive ? 'text-success-600' : 'text-danger-600'
                                    }`}>
                                    {isPositive ? (
                                        <TrendingUp className="w-4 h-4" />
                                    ) : (
                                        <TrendingDown className="w-4 h-4" />
                                    )}
                                    <div className="text-right">
                                        <p className="text-sm font-semibold">
                                            {isPositive ? '+' : ''}{index.change.toFixed(2)}
                                        </p>
                                        <p className="text-xs">
                                            ({isPositive ? '+' : ''}{index.changePercent.toFixed(2)}%)
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </motion.div>
                    )
                })}
            </div>

            <div className="mt-6 pt-4 border-t border-gray-200">
                <div className="flex items-center justify-between text-sm text-gray-600">
                    <span>Last updated: {new Date().toLocaleTimeString()}</span>
                    <div className="flex items-center space-x-1">
                        <Activity className="w-4 h-4" />
                        <span>Live feed active</span>
                    </div>
                </div>
            </div>
        </motion.div>
    )
}

export default LiveIndicesWidget 