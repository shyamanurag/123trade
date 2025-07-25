import React, { useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';

const TopBar = ({
    user,
    systemStatus,
    connectionStatus,
    darkMode,
    onToggleTheme,
    onToggleSidebar,
    onLogout
}) => {
    const [showUserMenu, setShowUserMenu] = useState(false);
    const [showNotifications, setShowNotifications] = useState(false);
    const userMenuRef = useRef(null);
    const notificationsRef = useRef(null);
    const location = useLocation();

    // Get page title based on current route
    const getPageTitle = () => {
        const path = location.pathname;
        const titles = {
            '/dashboard': 'Dashboard',
            '/trading': 'Trading Terminal',
            '/portfolio': 'Portfolio',
            '/analytics': 'Analytics',
            '/risk': 'Risk Management',
            '/market-data': 'Market Data',
            '/orders': 'Order Management',
            '/system': 'System Status',
            '/settings': 'Settings'
        };
        return titles[path] || 'ShareKhan Trading';
    };

    // Close menus when clicking outside
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (userMenuRef.current && !userMenuRef.current.contains(event.target)) {
                setShowUserMenu(false);
            }
            if (notificationsRef.current && !notificationsRef.current.contains(event.target)) {
                setShowNotifications(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const getConnectionStatusInfo = () => {
        switch (connectionStatus) {
            case 'connected':
                return { text: 'Connected', color: 'success', icon: '🟢' };
            case 'disconnected':
                return { text: 'Disconnected', color: 'error', icon: '🔴' };
            case 'connecting':
                return { text: 'Connecting', color: 'warning', icon: '🟡' };
            default:
                return { text: 'Unknown', color: 'secondary', icon: '⚪' };
        }
    };

    const statusInfo = getConnectionStatusInfo();

    // Mock notifications
    const notifications = [
        {
            id: 1,
            type: 'success',
            title: 'Order Executed',
            message: 'Buy order for RELIANCE executed at ₹2,485',
            time: '2 minutes ago',
            read: false
        },
        {
            id: 2,
            type: 'warning',
            title: 'Risk Alert',
            message: 'Position size approaching daily limit',
            time: '5 minutes ago',
            read: false
        },
        {
            id: 3,
            type: 'info',
            title: 'Market Update',
            message: 'NIFTY crosses 18,000 levels',
            time: '10 minutes ago',
            read: true
        }
    ];

    const unreadCount = notifications.filter(n => !n.read).length;

    return (
        <div className="topbar">
            <div className="topbar-left">
                <button
                    className="topbar-toggle"
                    onClick={onToggleSidebar}
                    title="Toggle Sidebar"
                >
                    ☰
                </button>

                <div className="topbar-breadcrumb">
                    {getPageTitle()}
                </div>

                {/* Market Status */}
                <div className="market-status">
                    <span className="market-time">
                        {new Date().toLocaleTimeString('en-IN', {
                            timeZone: 'Asia/Kolkata',
                            hour: '2-digit',
                            minute: '2-digit'
                        })}
                    </span>
                    <span className="market-session">
                        Market Open
                    </span>
                </div>
            </div>

            <div className="topbar-right">
                {/* System Status */}
                <div className={`status-indicator ${connectionStatus}`}>
                    <span className="status-dot"></span>
                    <span className="status-text">{statusInfo.text}</span>
                </div>

                {/* ShareKhan Status */}
                <div className="sharekhan-status">
                    <span className="sk-icon">SK</span>
                    <span className="sk-text">Connected</span>
                </div>

                {/* Quick Stats */}
                <div className="quick-stats">
                    <div className="stat-item">
                        <span className="stat-label">NIFTY</span>
                        <span className="stat-value text-success">18,245.60</span>
                        <span className="stat-change text-success">+0.45%</span>
                    </div>
                </div>

                {/* Notifications */}
                <div className="topbar-item" ref={notificationsRef}>
                    <button
                        className="notification-btn"
                        onClick={() => setShowNotifications(!showNotifications)}
                        title="Notifications"
                    >
                        🔔
                        {unreadCount > 0 && (
                            <span className="notification-badge">{unreadCount}</span>
                        )}
                    </button>

                    {showNotifications && (
                        <div className="notification-dropdown">
                            <div className="dropdown-header">
                                <h4>Notifications</h4>
                                <span className="mark-all-read">Mark all read</span>
                            </div>
                            <div className="notification-list">
                                {notifications.map((notification) => (
                                    <div
                                        key={notification.id}
                                        className={`notification-item ${notification.read ? 'read' : 'unread'}`}
                                    >
                                        <div className={`notification-type ${notification.type}`}>
                                            {notification.type === 'success' && '✅'}
                                            {notification.type === 'warning' && '⚠️'}
                                            {notification.type === 'info' && 'ℹ️'}
                                        </div>
                                        <div className="notification-content">
                                            <div className="notification-title">{notification.title}</div>
                                            <div className="notification-message">{notification.message}</div>
                                            <div className="notification-time">{notification.time}</div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                            <div className="dropdown-footer">
                                <a href="/notifications">View all notifications</a>
                            </div>
                        </div>
                    )}
                </div>

                {/* Theme Toggle */}
                <button
                    className="theme-toggle"
                    onClick={onToggleTheme}
                    title={`Switch to ${darkMode ? 'light' : 'dark'} theme`}
                >
                    {darkMode ? '☀️' : '🌙'}
                </button>

                {/* User Menu */}
                <div className="topbar-item" ref={userMenuRef}>
                    <button
                        className="user-menu-btn"
                        onClick={() => setShowUserMenu(!showUserMenu)}
                    >
                        <div className="user-avatar">
                            {user?.displayName?.charAt(0) || user?.username?.charAt(0) || 'U'}
                        </div>
                        <span className="user-name">
                            {user?.displayName || user?.username || 'User'}
                        </span>
                        <span className="dropdown-arrow">▼</span>
                    </button>

                    {showUserMenu && (
                        <div className="user-dropdown">
                            <div className="dropdown-header">
                                <div className="user-info">
                                    <div className="user-name">
                                        {user?.displayName || user?.username}
                                    </div>
                                    <div className="user-email">
                                        {user?.email}
                                    </div>
                                    <div className="user-role">
                                        {user?.role || 'Trader'}
                                    </div>
                                </div>
                            </div>

                            <div className="dropdown-menu">
                                <a href="/profile" className="dropdown-item">
                                    👤 Profile
                                </a>
                                <a href="/settings" className="dropdown-item">
                                    ⚙️ Settings
                                </a>
                                <a href="/trading-limits" className="dropdown-item">
                                    📊 Trading Limits
                                </a>
                                <a href="/api-keys" className="dropdown-item">
                                    🔑 API Keys
                                </a>
                                <div className="dropdown-divider"></div>
                                <a href="/help" className="dropdown-item">
                                    ❓ Help & Support
                                </a>
                                <button
                                    className="dropdown-item logout-btn"
                                    onClick={onLogout}
                                >
                                    🚪 Logout
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default TopBar; 