import React, { useEffect, useState } from 'react';
import { Navigate, Route, BrowserRouter as Router, Routes } from 'react-router-dom';
import './App.css';

// Components
import Analytics from './components/Analytics';
import Dashboard from './components/Dashboard';
import ErrorBoundary from './components/ErrorBoundary';
import LoadingSpinner from './components/LoadingSpinner';
import MarketData from './components/MarketData';
import Orders from './components/Orders';
import Portfolio from './components/Portfolio';
import RiskManagement from './components/RiskManagement';
import Settings from './components/Settings';
import ShareKhanAuth from './components/ShareKhanAuth';
import Sidebar from './components/Sidebar';
import SystemStatus from './components/SystemStatus';
import TopBar from './components/TopBar';
import Trading from './components/Trading';

// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://quantumcrypto-l43mb.ondigitalocean.app';

function App() {
    const [user, setUser] = useState(null);
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [loading, setLoading] = useState(true);
    const [darkMode, setDarkMode] = useState(true);
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
    const [systemStatus, setSystemStatus] = useState({});
    const [connectionStatus, setConnectionStatus] = useState('connecting');

    // Initialize application
    useEffect(() => {
        initializeApp();
        checkSystemStatus();
        setupEventListeners();
    }, []);

    const initializeApp = async () => {
        try {
            // Check for saved theme
            const savedTheme = localStorage.getItem('theme');
            if (savedTheme) {
                setDarkMode(savedTheme === 'dark');
            }

            // Check authentication status
            await checkAuthStatus();

            // Load user preferences
            loadUserPreferences();

        } catch (error) {
            console.error('Failed to initialize app:', error);
        } finally {
            setLoading(false);
        }
    };

    const checkAuthStatus = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/auth/status`, {
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (response.ok) {
                const data = await response.json();
                if (data.authenticated) {
                    setUser(data.user);
                    setIsAuthenticated(true);
                }
            }
        } catch (error) {
            console.error('Auth check failed:', error);
            setIsAuthenticated(false);
        }
    };

    const checkSystemStatus = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/system/status`);
            if (response.ok) {
                const status = await response.json();
                setSystemStatus(status);
                setConnectionStatus('connected');
            } else {
                setConnectionStatus('disconnected');
            }
        } catch (error) {
            console.error('System status check failed:', error);
            setConnectionStatus('error');
        }
    };

    const loadUserPreferences = () => {
        try {
            const preferences = localStorage.getItem('userPreferences');
            if (preferences) {
                const prefs = JSON.parse(preferences);
                setSidebarCollapsed(prefs.sidebarCollapsed || false);
            }
        } catch (error) {
            console.error('Failed to load preferences:', error);
        }
    };

    const setupEventListeners = () => {
        // System status polling
        const statusInterval = setInterval(checkSystemStatus, 30000);

        // Cleanup
        return () => {
            clearInterval(statusInterval);
        };
    };

    const handleLogin = (userData) => {
        setUser(userData);
        setIsAuthenticated(true);
    };

    const handleLogout = async () => {
        try {
            await fetch(`${API_BASE_URL}/api/auth/logout`, {
                method: 'POST',
                credentials: 'include'
            });
        } catch (error) {
            console.error('Logout failed:', error);
        } finally {
            setUser(null);
            setIsAuthenticated(false);
            localStorage.removeItem('userPreferences');
        }
    };

    const toggleTheme = () => {
        const newTheme = !darkMode;
        setDarkMode(newTheme);
        localStorage.setItem('theme', newTheme ? 'dark' : 'light');
    };

    const toggleSidebar = () => {
        const newCollapsed = !sidebarCollapsed;
        setSidebarCollapsed(newCollapsed);

        // Save preference
        const preferences = JSON.parse(localStorage.getItem('userPreferences') || '{}');
        preferences.sidebarCollapsed = newCollapsed;
        localStorage.setItem('userPreferences', JSON.stringify(preferences));
    };

    if (loading) {
        return (
            <div className="app-loading">
                <LoadingSpinner size="large" />
                <p>Initializing ShareKhan Trading System...</p>
            </div>
        );
    }

    return (
        <ErrorBoundary>
            <div className={`app ${darkMode ? 'dark-theme' : 'light-theme'}`}>
                <Router>
                    {!isAuthenticated ? (
                        <ShareKhanAuth onLogin={handleLogin} />
                    ) : (
                        <div className="app-layout">
                            <Sidebar
                                collapsed={sidebarCollapsed}
                                onToggle={toggleSidebar}
                                user={user}
                            />

                            <div className={`main-content ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
                                <TopBar
                                    user={user}
                                    systemStatus={systemStatus}
                                    connectionStatus={connectionStatus}
                                    darkMode={darkMode}
                                    onToggleTheme={toggleTheme}
                                    onToggleSidebar={toggleSidebar}
                                    onLogout={handleLogout}
                                />

                                <div className="content-area">
                                    <Routes>
                                        <Route path="/" element={<Dashboard />} />
                                        <Route path="/dashboard" element={<Dashboard />} />
                                        <Route path="/trading" element={<Trading />} />
                                        <Route path="/portfolio" element={<Portfolio />} />
                                        <Route path="/analytics" element={<Analytics />} />
                                        <Route path="/risk" element={<RiskManagement />} />
                                        <Route path="/market-data" element={<MarketData />} />
                                        <Route path="/orders" element={<Orders />} />
                                        <Route path="/system" element={<SystemStatus />} />
                                        <Route path="/settings" element={<Settings />} />
                                        <Route path="*" element={<Navigate to="/dashboard" />} />
                                    </Routes>
                                </div>
                            </div>
                        </div>
                    )}
                </Router>
            </div>
        </ErrorBoundary>
    );
}

export default App; 