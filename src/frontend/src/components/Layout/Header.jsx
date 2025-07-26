import { AnimatePresence, motion } from 'framer-motion'
import { Bell, LogOut, Menu, RefreshCw, User, Wifi, WifiOff } from 'lucide-react'
import React, { useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import { useWebSocket } from '../../context/WebSocketContext'

const Header = ({ onMenuClick }) => {
    const { user, logout } = useAuth()
    const { isConnected, connectionStatus, tradingAlerts } = useWebSocket()
    const [showNotifications, setShowNotifications] = useState(false)
    const [showUserMenu, setShowUserMenu] = useState(false)

    const unreadAlerts = tradingAlerts.filter(alert => !alert.read).length

    const getConnectionIcon = () => {
        if (isConnected && connectionStatus === 'connected') {
            return <Wifi className="w-4 h-4 text-success-600" />
        }
        return <WifiOff className="w-4 h-4 text-danger-600" />
    }

    const getConnectionText = () => {
        switch (connectionStatus) {
            case 'connected':
                return 'Connected'
            case 'connecting':
                return 'Connecting...'
            case 'disconnected':
                return 'Disconnected'
            case 'error':
                return 'Connection Error'
            case 'failed':
                return 'Connection Failed'
            default:
                return 'Unknown'
        }
    }

    const handleLogout = async () => {
        await logout()
        setShowUserMenu(false)
    }

    return (
        <header className="bg-white border-b border-gray-200 px-6 py-4">
            <div className="flex items-center justify-between">
                {/* Left Section */}
                <div className="flex items-center space-x-4">
                    <button
                        onClick={onMenuClick}
                        className="p-2 rounded-lg hover:bg-gray-100 transition-colors lg:hidden"
                    >
                        <Menu className="w-5 h-5 text-gray-600" />
                    </button>

                    <div className="hidden lg:block">
                        <h2 className="text-xl font-semibold text-gray-900">Trading Dashboard</h2>
                        <p className="text-sm text-gray-500">Welcome back, {user?.name || 'Trader'}</p>
                    </div>
                </div>

                {/* Right Section */}
                <div className="flex items-center space-x-4">
                    {/* Connection Status */}
                    <div className="hidden md:flex items-center space-x-2 px-3 py-1.5 bg-gray-50 rounded-lg">
                        {getConnectionIcon()}
                        <span className="text-sm font-medium text-gray-700">
                            {getConnectionText()}
                        </span>
                    </div>

                    {/* Notifications */}
                    <div className="relative">
                        <button
                            onClick={() => setShowNotifications(!showNotifications)}
                            className="relative p-2 rounded-lg hover:bg-gray-100 transition-colors"
                        >
                            <Bell className="w-5 h-5 text-gray-600" />
                            {unreadAlerts > 0 && (
                                <motion.span
                                    initial={{ scale: 0 }}
                                    animate={{ scale: 1 }}
                                    className="absolute -top-1 -right-1 w-5 h-5 bg-danger-500 text-white text-xs rounded-full flex items-center justify-center"
                                >
                                    {unreadAlerts > 9 ? '9+' : unreadAlerts}
                                </motion.span>
                            )}
                        </button>

                        <AnimatePresence>
                            {showNotifications && (
                                <motion.div
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: 10 }}
                                    className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-lg border border-gray-200 z-50"
                                >
                                    <div className="p-4 border-b border-gray-200">
                                        <h3 className="font-semibold text-gray-900">Trading Alerts</h3>
                                        <p className="text-sm text-gray-500">
                                            {unreadAlerts} new alerts
                                        </p>
                                    </div>

                                    <div className="max-h-64 overflow-y-auto">
                                        {tradingAlerts.length > 0 ? (
                                            tradingAlerts.slice(0, 5).map((alert, index) => (
                                                <div
                                                    key={index}
                                                    className={`p-3 border-b border-gray-100 last:border-b-0 ${!alert.read ? 'bg-primary-50' : ''
                                                        }`}
                                                >
                                                    <div className="flex items-start space-x-3">
                                                        <div className={`w-2 h-2 rounded-full mt-2 ${alert.priority === 'high' ? 'bg-danger-500' :
                                                                alert.priority === 'medium' ? 'bg-warning-500' :
                                                                    'bg-success-500'
                                                            }`} />
                                                        <div className="flex-1 min-w-0">
                                                            <p className="text-sm font-medium text-gray-900 truncate">
                                                                {alert.title || 'Trading Alert'}
                                                            </p>
                                                            <p className="text-sm text-gray-600 mt-1">
                                                                {alert.message}
                                                            </p>
                                                            <p className="text-xs text-gray-500 mt-1">
                                                                {new Date(alert.timestamp).toLocaleTimeString()}
                                                            </p>
                                                        </div>
                                                    </div>
                                                </div>
                                            ))
                                        ) : (
                                            <div className="p-4 text-center text-gray-500">
                                                <Bell className="w-8 h-8 mx-auto mb-2 opacity-50" />
                                                <p>No alerts yet</p>
                                            </div>
                                        )}
                                    </div>

                                    {tradingAlerts.length > 5 && (
                                        <div className="p-3 border-t border-gray-200 text-center">
                                            <button className="text-sm text-primary-600 hover:text-primary-700 font-medium">
                                                View all alerts
                                            </button>
                                        </div>
                                    )}
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>

                    {/* User Menu */}
                    <div className="relative">
                        <button
                            onClick={() => setShowUserMenu(!showUserMenu)}
                            className="flex items-center space-x-2 p-2 rounded-lg hover:bg-gray-100 transition-colors"
                        >
                            <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center">
                                <User className="w-4 h-4 text-white" />
                            </div>
                            <span className="hidden md:block text-sm font-medium text-gray-700">
                                {user?.name || 'User'}
                            </span>
                        </button>

                        <AnimatePresence>
                            {showUserMenu && (
                                <motion.div
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: 10 }}
                                    className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 z-50"
                                >
                                    <div className="p-3 border-b border-gray-200">
                                        <p className="font-medium text-gray-900">{user?.name || 'User'}</p>
                                        <p className="text-sm text-gray-500">{user?.email || 'user@example.com'}</p>
                                    </div>

                                    <div className="p-1">
                                        <button className="w-full flex items-center space-x-2 px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 rounded-lg transition-colors">
                                            <User className="w-4 h-4" />
                                            <span>Profile</span>
                                        </button>

                                        <button className="w-full flex items-center space-x-2 px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 rounded-lg transition-colors">
                                            <RefreshCw className="w-4 h-4" />
                                            <span>Refresh Token</span>
                                        </button>

                                        <hr className="my-1 border-gray-200" />

                                        <button
                                            onClick={handleLogout}
                                            className="w-full flex items-center space-x-2 px-3 py-2 text-left text-sm text-danger-600 hover:bg-danger-50 rounded-lg transition-colors"
                                        >
                                            <LogOut className="w-4 h-4" />
                                            <span>Sign Out</span>
                                        </button>
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </div>
            </div>
        </header>
    )
}

export default Header 