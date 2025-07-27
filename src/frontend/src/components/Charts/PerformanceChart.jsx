import { motion } from 'framer-motion'
import { Activity, TrendingDown, TrendingUp } from 'lucide-react'
import React from 'react'
import {
    Area,
    AreaChart,
    CartesianGrid,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis
} from 'recharts'

const PerformanceChart = ({ data }) => {
    // Mock data if none provided
    const defaultData = [
        { date: '2025-01-01', value: 100000, pnl: 0 },
        { date: '2025-01-02', value: 102500, pnl: 2500 },
        { date: '2025-01-03', value: 101800, pnl: 1800 },
        { date: '2025-01-04', value: 105200, pnl: 5200 },
        { date: '2025-01-05', value: 103900, pnl: 3900 },
        { date: '2025-01-06', value: 108500, pnl: 8500 },
        { date: '2025-01-07', value: 107200, pnl: 7200 }
    ]

    const chartData = data || defaultData
    const latestValue = chartData[chartData.length - 1]
    const previousValue = chartData[chartData.length - 2]
    const change = latestValue?.value - previousValue?.value || 0
    const changePercent = previousValue?.value ? ((change / previousValue.value) * 100) : 0
    const isPositive = change >= 0

    const CustomTooltip = ({ active, payload, label }) => {
        if (active && payload && payload.length) {
            return (
                <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
                    <p className="text-sm font-medium text-gray-900 mb-1">
                        {new Date(label).toLocaleDateString()}
                    </p>
                    <p className="text-sm text-primary-600">
                        Value: ₹{payload[0].value.toLocaleString()}
                    </p>
                    {payload[1] && (
                        <p className={`text-sm ${payload[1].value >= 0 ? 'text-success-600' : 'text-danger-600'}`}>
                            P&L: ₹{payload[1].value.toLocaleString()}
                        </p>
                    )}
                </div>
            )
        }
        return null
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="card"
        >
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-1">
                        Portfolio Performance
                    </h3>
                    <p className="text-sm text-gray-600">
                        7-day performance overview
                    </p>
                </div>

                <div className="flex items-center space-x-4">
                    <div className="text-right">
                        <p className="text-2xl font-bold text-gray-900">
                            ₹{latestValue?.value.toLocaleString()}
                        </p>
                        <div className={`flex items-center space-x-1 ${isPositive ? 'text-success-600' : 'text-danger-600'}`}>
                            {isPositive ? (
                                <TrendingUp className="w-4 h-4" />
                            ) : (
                                <TrendingDown className="w-4 h-4" />
                            )}
                            <span className="text-sm font-medium">
                                {isPositive ? '+' : ''}₹{change.toLocaleString()} ({changePercent.toFixed(2)}%)
                            </span>
                        </div>
                    </div>

                    <div className="w-12 h-12 rounded-lg bg-primary-100 flex items-center justify-center">
                        <Activity className="w-6 h-6 text-primary-600" />
                    </div>
                </div>
            </div>

            <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                        <defs>
                            <linearGradient id="valueGradient" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                        <XAxis
                            dataKey="date"
                            stroke="#64748b"
                            fontSize={12}
                            tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                        />
                        <YAxis
                            stroke="#64748b"
                            fontSize={12}
                            tickFormatter={(value) => `₹${(value / 1000).toFixed(0)}K`}
                        />
                        <Tooltip content={<CustomTooltip />} />
                        <Area
                            type="monotone"
                            dataKey="value"
                            stroke="#3B82F6"
                            strokeWidth={2}
                            fill="url(#valueGradient)"
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>

            <div className="mt-6 grid grid-cols-3 divide-x divide-gray-200">
                <div className="text-center">
                    <p className="text-sm text-gray-600 mb-1">Total P&L</p>
                    <p className={`text-lg font-semibold ${latestValue?.pnl >= 0 ? 'text-success-600' : 'text-danger-600'}`}>
                        ₹{latestValue?.pnl.toLocaleString()}
                    </p>
                </div>
                <div className="text-center">
                    <p className="text-sm text-gray-600 mb-1">Best Day</p>
                    <p className="text-lg font-semibold text-success-600">
                        ₹{Math.max(...chartData.map(d => d.pnl)).toLocaleString()}
                    </p>
                </div>
                <div className="text-center">
                    <p className="text-sm text-gray-600 mb-1">Worst Day</p>
                    <p className="text-lg font-semibold text-danger-600">
                        ₹{Math.min(...chartData.map(d => d.pnl)).toLocaleString()}
                    </p>
                </div>
            </div>
        </motion.div>
    )
}

export default PerformanceChart 