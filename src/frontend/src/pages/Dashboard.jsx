import { motion } from 'framer-motion'
import {
    Activity,
    AlertCircle,
    DollarSign,
    TrendingDown,
    TrendingUp,
    Users,
    Wifi,
    WifiOff
} from 'lucide-react'
import React from 'react'
import { useQuery } from 'react-query'
import PerformanceChart from '../components/Charts/PerformanceChart'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import LiveIndicesWidget from '../components/Widgets/LiveIndicesWidget'
import RecentTradesWidget from '../components/Widgets/RecentTradesWidget'
import { useWebSocket } from '../context/WebSocketContext'
import { apiService } from '../services/apiService'

const Dashboard = () => {
    const { isConnected, liveIndices, marketData } = useWebSocket()

    const { data: dashboardData, isLoading, error } = useQuery(
        'dashboard',
        apiService.getDashboardData,
        {
            refetchInterval: 30000, // Refresh every 30 seconds
            staleTime: 10000
        }
    )

    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <LoadingSpinner size="large" text="Loading dashboard..." />
            </div>
        )
    }

    if (error) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center">
                    <AlertCircle className="w-16 h-16 text-danger-500 mx-auto mb-4" />
                    <h2 className="text-xl font-semibold text-gray-900 mb-2">Dashboard Error</h2>
                    <p className="text-gray-600">{error.message}</p>
                </div>
            </div>
        )
    }

    const metrics = dashboardData?.metrics || {}
    const recentTrades = dashboardData?.recent_trades || []
    const alerts = dashboardData?.alerts || []

    const metricCards = [
        {
            title: 'Total Portfolio Value',
            value: `₹${(metrics.portfolio_value || 0).toLocaleString()}`,
            change: metrics.portfolio_change || 0,
            icon: DollarSign,
            color: 'primary'
        },
        {
            title: 'Today\'s P&L',
            value: `₹${(metrics.todays_pnl || 0).toLocaleString()}`,
            change: metrics.pnl_percentage || 0,
            icon: TrendingUp,
            color: metrics.todays_pnl >= 0 ? 'success' : 'danger'
        },
        {
            title: 'Active Positions',
            value: metrics.active_positions || 0,
            change: metrics.positions_change || 0,
            icon: Activity,
            color: 'warning'
        },
        {
            title: 'Connected Users',
            value: metrics.connected_users || 0,
            change: 0,
            icon: Users,
            color: 'primary'
        }
    ]

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
        hidden: { opacity: 0, y: 20 },
        visible: {
            opacity: 1,
            y: 0,
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
            className="space-y-6"
        >
            {/* Header */}
            <motion.div variants={itemVariants} className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Trading Dashboard</h1>
                    <p className="text-gray-600 mt-1">
                        Real-time market overview and portfolio performance
                    </p>
                </div>

                <div className="flex items-center space-x-3 mt-4 sm:mt-0">
                    <div className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg ${isConnected ? 'bg-success-50 text-success-700' : 'bg-danger-50 text-danger-700'
                        }`}>
                        {isConnected ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
                        <span className="text-sm font-medium">
                            {isConnected ? 'Live Data' : 'Disconnected'}
                        </span>
                    </div>

                    <span className="text-sm text-gray-500">
                        Last updated: {new Date().toLocaleTimeString()}
                    </span>
                </div>
            </motion.div>

            {/* Metric Cards */}
            <motion.div
                variants={itemVariants}
                className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
            >
                {metricCards.map((metric, index) => {
                    const Icon = metric.icon
                    const isPositive = metric.change >= 0

                    return (
                        <motion.div
                            key={metric.title}
                            variants={itemVariants}
                            className="metric-card group cursor-pointer"
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                        >
                            <div className="flex items-center justify-between">
                                <div className="flex-1">
                                    <p className="text-sm font-medium text-gray-600 mb-1">
                                        {metric.title}
                                    </p>
                                    <p className="text-2xl font-bold text-gray-900 mb-2">
                                        {metric.value}
                                    </p>
                                    {metric.change !== 0 && (
                                        <div className={`flex items-center space-x-1 ${isPositive ? 'text-success-600' : 'text-danger-600'
                                            }`}>
                                            {isPositive ? (
                                                <TrendingUp className="w-4 h-4" />
                                            ) : (
                                                <TrendingDown className="w-4 h-4" />
                                            )}
                                            <span className="text-sm font-medium">
                                                {Math.abs(metric.change)}%
                                            </span>
                                        </div>
                                    )}
                                </div>

                                <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${metric.color === 'primary' ? 'bg-primary-100 text-primary-600' :
                                        metric.color === 'success' ? 'bg-success-100 text-success-600' :
                                            metric.color === 'danger' ? 'bg-danger-100 text-danger-600' :
                                                'bg-warning-100 text-warning-600'
                                    } group-hover:scale-110 transition-transform duration-200`}>
                                    <Icon className="w-6 h-6" />
                                </div>
                            </div>
                        </motion.div>
                    )
                })}
            </motion.div>

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Live Indices */}
                <motion.div variants={itemVariants} className="lg:col-span-2">
                    <LiveIndicesWidget indices={liveIndices} />
                </motion.div>

                {/* Recent Trades */}
                <motion.div variants={itemVariants}>
                    <RecentTradesWidget trades={recentTrades} />
                </motion.div>
            </div>

            {/* Performance Chart */}
            <motion.div variants={itemVariants}>
                <PerformanceChart data={dashboardData?.performance_data} />
            </motion.div>

            {/* Alerts & Notifications */}
            {alerts.length > 0 && (
                <motion.div variants={itemVariants} className="card">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-semibold text-gray-900">System Alerts</h3>
                        <span className="text-sm text-gray-500">{alerts.length} active</span>
                    </div>

                    <div className="space-y-3">
                        {alerts.slice(0, 3).map((alert, index) => (
                            <div
                                key={index}
                                className={`p-3 rounded-lg border-l-4 ${alert.priority === 'high' ? 'bg-danger-50 border-danger-400' :
                                        alert.priority === 'medium' ? 'bg-warning-50 border-warning-400' :
                                            'bg-primary-50 border-primary-400'
                                    }`}
                            >
                                <div className="flex items-start space-x-3">
                                    <AlertCircle className={`w-5 h-5 mt-0.5 ${alert.priority === 'high' ? 'text-danger-600' :
                                            alert.priority === 'medium' ? 'text-warning-600' :
                                                'text-primary-600'
                                        }`} />
                                    <div className="flex-1">
                                        <p className="font-medium text-gray-900">{alert.title}</p>
                                        <p className="text-sm text-gray-600 mt-1">{alert.message}</p>
                                        <p className="text-xs text-gray-500 mt-2">
                                            {new Date(alert.timestamp).toLocaleString()}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </motion.div>
            )}
        </motion.div>
    )
}

export default Dashboard 