import { motion } from 'framer-motion'
import { Activity, BarChart3, TrendingDown, TrendingUp } from 'lucide-react'
import React from 'react'

const LiveIndicesWidget = ({ indices }) => {
    // Mock data if none provided
    const defaultIndices = [
        {
            name: 'NIFTY 50',
            symbol: 'NIFTY',
            value: 22145.50,
            change: 125.30,
            changePercent: 0.57,
            lastUpdate: new Date().toISOString()
        },
        {
            name: 'SENSEX',
            symbol: 'SENSEX',
            value: 73042.20,
            change: -88.45,
            changePercent: -0.12,
            lastUpdate: new Date().toISOString()
        },
        {
            name: 'BANK NIFTY',
            symbol: 'BANKNIFTY',
            value: 45890.75,
            change: 234.60,
            changePercent: 0.51,
            lastUpdate: new Date().toISOString()
        },
        {
            name: 'NIFTY IT',
            symbol: 'NIFTYIT',
            value: 32156.40,
            change: -156.80,
            changePercent: -0.49,
            lastUpdate: new Date().toISOString()
        },
        {
            name: 'NIFTY AUTO',
            symbol: 'NIFTYAUTO',
            value: 18765.30,
            change: 89.20,
            changePercent: 0.48,
            lastUpdate: new Date().toISOString()
        },
        {
            name: 'NIFTY PHARMA',
            symbol: 'NIFTYPHARMA',
            value: 14532.85,
            change: -45.60,
            changePercent: -0.31,
            lastUpdate: new Date().toISOString()
        }
    ]

    const indicesData = indices || defaultIndices

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