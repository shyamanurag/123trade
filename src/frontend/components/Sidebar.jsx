import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';

const Sidebar = ({ collapsed, onToggle, user }) => {
    const location = useLocation();

    const navigationItems = [
        {
            section: 'Trading',
            items: [
                {
                    path: '/dashboard',
                    name: 'Dashboard',
                    icon: '📊',
                    description: 'Overview & Analytics'
                },
                {
                    path: '/trading',
                    name: 'Trading',
                    icon: '💱',
                    description: 'Place Orders'
                },
                {
                    path: '/portfolio',
                    name: 'Portfolio',
                    icon: '💰',
                    description: 'Holdings & P&L'
                },
                {
                    path: '/orders',
                    name: 'Orders',
                    icon: '📋',
                    description: 'Order History'
                }
            ]
        },
        {
            section: 'Analysis',
            items: [
                {
                    path: '/analytics',
                    name: 'Analytics',
                    icon: '📈',
                    description: 'Performance Analysis'
                },
                {
                    path: '/market-data',
                    name: 'Market Data',
                    icon: '📡',
                    description: 'Live Market Feed'
                },
                {
                    path: '/risk',
                    name: 'Risk Management',
                    icon: '🛡️',
                    description: 'Risk Controls'
                }
            ]
        },
        {
            section: 'System',
            items: [
                {
                    path: '/system',
                    name: 'System Status',
                    icon: '⚙️',
                    description: 'Health & Monitoring'
                },
                {
                    path: '/settings',
                    name: 'Settings',
                    icon: '🔧',
                    description: 'Configuration'
                }
            ]
        }
    ];

    return (
        <div className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
            {/* Sidebar Header */}
            <div className="sidebar-header">
                <div className="sidebar-logo">SK</div>
                <div className="sidebar-title">ShareKhan Pro</div>
            </div>

            {/* User Info */}
            <div className="sidebar-user">
                <div className="user-avatar">
                    {user?.displayName?.charAt(0) || user?.username?.charAt(0) || 'U'}
                </div>
                <div className="user-info">
                    <div className="user-name">
                        {user?.displayName || user?.username || 'User'}
                    </div>
                    <div className="user-role">
                        {user?.role || 'Trader'}
                    </div>
                </div>
            </div>

            {/* Navigation */}
            <nav className="sidebar-nav">
                {navigationItems.map((section) => (
                    <div key={section.section} className="nav-section">
                        <div className="nav-section-title">{section.section}</div>
                        {section.items.map((item) => (
                            <NavLink
                                key={item.path}
                                to={item.path}
                                className={({ isActive }) =>
                                    `nav-item ${isActive ? 'active' : ''}`
                                }
                                title={collapsed ? item.name : ''}
                            >
                                <span className="nav-item-icon">{item.icon}</span>
                                <div className="nav-item-content">
                                    <span className="nav-item-text">{item.name}</span>
                                    {!collapsed && (
                                        <span className="nav-item-description">{item.description}</span>
                                    )}
                                </div>
                            </NavLink>
                        ))}
                    </div>
                ))}
            </nav>

            {/* ShareKhan Status */}
            <div className="sidebar-footer">
                <div className="sharekhan-status">
                    <div className="status-indicator">
                        <span className="status-dot"></span>
                        <span className="status-text">ShareKhan Connected</span>
                    </div>
                    {!collapsed && (
                        <div className="status-details">
                            <div>Session: Active</div>
                            <div>Market: Open</div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default Sidebar; 