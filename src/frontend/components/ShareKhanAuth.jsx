import React, { useEffect, useState } from 'react';
import LoadingSpinner from './LoadingSpinner';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://quantumcrypto-l43mb.ondigitalocean.app';

const ShareKhanAuth = ({ onLogin }) => {
    const [authStep, setAuthStep] = useState('initial'); // initial, connecting, success, error
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [credentials, setCredentials] = useState({
        customerId: '',
        password: '',
        pin: ''
    });
    const [systemStatus, setSystemStatus] = useState({});

    useEffect(() => {
        checkSystemStatus();
    }, []);

    const checkSystemStatus = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/system/status`);
            if (response.ok) {
                const status = await response.json();
                setSystemStatus(status);
            }
        } catch (error) {
            console.error('Failed to check system status:', error);
        }
    };

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setCredentials(prev => ({
            ...prev,
            [name]: value
        }));
    };

    const handleShareKhanLogin = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setAuthStep('connecting');

        try {
            // Step 1: Initiate ShareKhan authentication
            const response = await fetch(`${API_BASE_URL}/api/auth/sharekhan/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(credentials)
            });

            const result = await response.json();

            if (response.ok) {
                if (result.success) {
                    setAuthStep('success');
                    // Call the onLogin callback with user data
                    onLogin(result.user);
                } else {
                    setError(result.message || 'Authentication failed');
                    setAuthStep('error');
                }
            } else {
                setError(result.message || 'Login request failed');
                setAuthStep('error');
            }
        } catch (error) {
            console.error('ShareKhan authentication failed:', error);
            setError('Connection failed. Please check your internet connection.');
            setAuthStep('error');
        } finally {
            setLoading(false);
        }
    };

    const handleRetry = () => {
        setAuthStep('initial');
        setError(null);
    };

    return (
        <div className="auth-container">
            <div className="auth-background">
                <div className="auth-overlay"></div>
            </div>

            <div className="auth-content">
                <div className="auth-card">
                    <div className="auth-header">
                        <div className="auth-logo">
                            <div className="logo-icon">SK</div>
                            <div className="logo-text">
                                <h1>ShareKhan Trading</h1>
                                <p>Professional Trading Platform</p>
                            </div>
                        </div>
                    </div>

                    <div className="auth-body">
                        {authStep === 'initial' && (
                            <>
                                <h2>Login to ShareKhan</h2>
                                <p className="auth-subtitle">
                                    Enter your ShareKhan credentials to access the trading platform
                                </p>

                                <form onSubmit={handleShareKhanLogin} className="auth-form">
                                    <div className="form-group">
                                        <label className="form-label">Customer ID</label>
                                        <input
                                            type="text"
                                            name="customerId"
                                            value={credentials.customerId}
                                            onChange={handleInputChange}
                                            className="form-input"
                                            placeholder="Enter your Customer ID"
                                            required
                                        />
                                    </div>

                                    <div className="form-group">
                                        <label className="form-label">Password</label>
                                        <input
                                            type="password"
                                            name="password"
                                            value={credentials.password}
                                            onChange={handleInputChange}
                                            className="form-input"
                                            placeholder="Enter your password"
                                            required
                                        />
                                    </div>

                                    <div className="form-group">
                                        <label className="form-label">Trading PIN</label>
                                        <input
                                            type="password"
                                            name="pin"
                                            value={credentials.pin}
                                            onChange={handleInputChange}
                                            className="form-input"
                                            placeholder="Enter your trading PIN"
                                            required
                                            maxLength="6"
                                        />
                                    </div>

                                    <button
                                        type="submit"
                                        className="btn btn-primary btn-lg auth-submit"
                                        disabled={loading}
                                    >
                                        {loading ? (
                                            <>
                                                <LoadingSpinner size="small" color="white" />
                                                Connecting...
                                            </>
                                        ) : (
                                            'Login to ShareKhan'
                                        )}
                                    </button>
                                </form>

                                {error && (
                                    <div className="auth-error">
                                        <div className="error-icon">⚠️</div>
                                        <div className="error-message">{error}</div>
                                        <button className="btn btn-secondary btn-sm" onClick={handleRetry}>
                                            Try Again
                                        </button>
                                    </div>
                                )}
                            </>
                        )}

                        {authStep === 'connecting' && (
                            <div className="auth-connecting">
                                <LoadingSpinner size="large" />
                                <h3>Connecting to ShareKhan</h3>
                                <p>Please wait while we authenticate your credentials...</p>
                                <div className="connecting-steps">
                                    <div className="step active">✓ Validating credentials</div>
                                    <div className="step">⏳ Establishing connection</div>
                                    <div className="step">⏳ Loading trading data</div>
                                </div>
                            </div>
                        )}

                        {authStep === 'success' && (
                            <div className="auth-success">
                                <div className="success-icon">✅</div>
                                <h3>Successfully Connected!</h3>
                                <p>Welcome to ShareKhan Trading Platform</p>
                                <LoadingSpinner size="small" text="Loading dashboard..." />
                            </div>
                        )}

                        {authStep === 'error' && (
                            <div className="auth-error">
                                <div className="error-icon">❌</div>
                                <h3>Authentication Failed</h3>
                                <p>{error}</p>
                                <div className="error-actions">
                                    <button className="btn btn-primary" onClick={handleRetry}>
                                        Try Again
                                    </button>
                                    <button className="btn btn-secondary" onClick={() => window.location.reload()}>
                                        Refresh Page
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>

                    <div className="auth-footer">
                        <div className="system-status">
                            <div className="status-item">
                                <span className="status-label">System:</span>
                                <span className={`status-value ${systemStatus.healthy ? 'success' : 'error'}`}>
                                    {systemStatus.healthy ? 'Online' : 'Offline'}
                                </span>
                            </div>
                            <div className="status-item">
                                <span className="status-label">Market:</span>
                                <span className="status-value success">Open</span>
                            </div>
                        </div>

                        <div className="auth-links">
                            <a href="/help" className="auth-link">Need Help?</a>
                            <a href="/forgot-password" className="auth-link">Forgot Password?</a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ShareKhanAuth; 