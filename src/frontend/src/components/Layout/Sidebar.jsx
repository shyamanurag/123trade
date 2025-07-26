import { AnimatePresence, motion } from 'framer-motion'
import {
    Activity,
    BarChart3,
    DollarSign,
    Home,
    Key,
    Network,
    Settings,
    TrendingUp,
    Users,
    X
} from 'lucide-react'
import React from 'react'
import { NavLink, useLocation } from 'react-router-dom'

const Sidebar = ({ isOpen, onClose }) => {
    const location = useLocation()

    const navigationItems = [
        {
            name: 'Dashboard',
            href: '/dashboard',
            icon: Home,
            description: 'Overview & Analytics'
        },
        {
            name: 'Live Indices',
            href: '/live-indices',
            icon: TrendingUp,
            description: 'Real-time Market Data'
        },
        {
            name: 'Analytics',
            href: '/analytics',
            icon: BarChart3,
            description: 'Performance & Insights'
        },
        {
            name: 'Trades',
            href: '/trades',
            icon: DollarSign,
            description: 'Trade History & Details'
        },
        {
            name: 'Users',
            href: '/users',
            icon: Users,
            description: 'User Management'
        },
        {
            name: 'Auth Tokens',
            href: '/auth-tokens',
            icon: Key,
            description: 'Daily Token Management'
        },
        {
            name: 'Multi-User API',
            href: '/multi-user-api',
            icon: Network,
            description: 'API Submission Portal'
        },
        {
            name: 'Settings',
            href: '/settings',
            icon: Settings,
            description: 'System Configuration'
        }
    ]

    const sidebarVariants = {
        open: {
            width: '16rem',
            transition: {
                duration: 0.3,
                ease: 'easeInOut'
            }
        },
        closed: {
            width: '5rem',
            transition: {
                duration: 0.3,
                ease: 'easeInOut'
            }
        }
    }

    const itemVariants = {
        open: {
            opacity: 1,
            x: 0,
            transition: {
                duration: 0.3,
                ease: 'easeOut'
            }
        },
        closed: {
            opacity: 0,
            x: -20,
            transition: {
                duration: 0.2,
                ease: 'easeIn'
            }
        }
    }

    return (
        <>
            {/* Desktop Sidebar */}
            <motion.aside
                variants={sidebarVariants}
                animate={isOpen ? 'open' : 'closed'}
                className="fixed left-0 top-0 z-50 h-full bg-white border-r border-gray-200 shadow-lg lg:block hidden"
            >
                <div className="flex flex-col h-full">
                    {/* Logo & Brand */}
                    <div className="p-4 border-b border-gray-200">
                        <div className="flex items-center space-x-3">
                            <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-primary-700 rounded-lg flex items-center justify-center">
                                <Activity className="w-6 h-6 text-white" />
                            </div>
                            <AnimatePresence>
                                {isOpen && (
                                    <motion.div
                                        variants={itemVariants}
                                        initial="closed"
                                        animate="open"
                                        exit="closed"
                                        className="flex flex-col"
                                    >
                                        <h1 className="text-lg font-bold text-gray-900">Trade123</h1>
                                        <p className="text-xs text-gray-500">Trading Platform</p>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>
                    </div>

                    {/* Navigation */}
                    <nav className="flex-1 p-4 space-y-2">
                        {navigationItems.map((item) => {
                            const Icon = item.icon
                            const isActive = location.pathname === item.href

                            return (
                                <NavLink
                                    key={item.name}
                                    to={item.href}
                                    className={({ isActive }) =>
                                        `flex items-center space-x-3 px-3 py-2.5 rounded-lg transition-all duration-200 group ${isActive
                                            ? 'bg-primary-50 text-primary-700 border border-primary-200'
                                            : 'text-gray-700 hover:bg-gray-50 hover:text-primary-600'
                                        }`
                                    }
                                >
                                    <Icon className={`w-5 h-5 ${isActive ? 'text-primary-600' : 'text-gray-500 group-hover:text-primary-500'}`} />

                                    <AnimatePresence>
                                        {isOpen && (
                                            <motion.div
                                                variants={itemVariants}
                                                initial="closed"
                                                animate="open"
                                                exit="closed"
                                                className="flex flex-col min-w-0 flex-1"
                                            >
                                                <span className="font-medium truncate">{item.name}</span>
                                                <span className="text-xs text-gray-500 truncate">{item.description}</span>
                                            </motion.div>
                                        )}
                                    </AnimatePresence>
                                </NavLink>
                            )
                        })}
                    </nav>

                    {/* Footer */}
                    <div className="p-4 border-t border-gray-200">
                        <AnimatePresence>
                            {isOpen && (
                                <motion.div
                                    variants={itemVariants}
                                    initial="closed"
                                    animate="open"
                                    exit="closed"
                                    className="text-xs text-gray-500 text-center"
                                >
                                    <p>© 2025 Trade123</p>
                                    <p>Advanced Trading Platform</p>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </div>
            </motion.aside>

            {/* Mobile Sidebar */}
            <AnimatePresence>
                {isOpen && (
                    <motion.aside
                        initial={{ x: '-100%' }}
                        animate={{ x: 0 }}
                        exit={{ x: '-100%' }}
                        transition={{ duration: 0.3, ease: 'easeInOut' }}
                        className="fixed left-0 top-0 z-50 h-full w-64 bg-white border-r border-gray-200 shadow-lg lg:hidden"
                    >
                        <div className="flex flex-col h-full">
                            {/* Header with Close Button */}
                            <div className="flex items-center justify-between p-4 border-b border-gray-200">
                                <div className="flex items-center space-x-3">
                                    <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-primary-700 rounded-lg flex items-center justify-center">
                                        <Activity className="w-6 h-6 text-white" />
                                    </div>
                                    <div>
                                        <h1 className="text-lg font-bold text-gray-900">Trade123</h1>
                                        <p className="text-xs text-gray-500">Trading Platform</p>
                                    </div>
                                </div>
                                <button
                                    onClick={onClose}
                                    className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
                                >
                                    <X className="w-5 h-5 text-gray-500" />
                                </button>
                            </div>

                            {/* Navigation */}
                            <nav className="flex-1 p-4 space-y-2">
                                {navigationItems.map((item) => {
                                    const Icon = item.icon
                                    const isActive = location.pathname === item.href

                                    return (
                                        <NavLink
                                            key={item.name}
                                            to={item.href}
                                            onClick={onClose}
                                            className={({ isActive }) =>
                                                `flex items-center space-x-3 px-3 py-2.5 rounded-lg transition-all duration-200 ${isActive
                                                    ? 'bg-primary-50 text-primary-700 border border-primary-200'
                                                    : 'text-gray-700 hover:bg-gray-50 hover:text-primary-600'
                                                }`
                                            }
                                        >
                                            <Icon className={`w-5 h-5 ${isActive ? 'text-primary-600' : 'text-gray-500'}`} />
                                            <div className="flex flex-col min-w-0 flex-1">
                                                <span className="font-medium truncate">{item.name}</span>
                                                <span className="text-xs text-gray-500 truncate">{item.description}</span>
                                            </div>
                                        </NavLink>
                                    )
                                })}
                            </nav>
                        </div>
                    </motion.aside>
                )}
            </AnimatePresence>
        </>
    )
}

export default Sidebar 