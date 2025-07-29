import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { useEffect, useState } from 'react';

// Add axios interceptor for authentication
axios.interceptors.request.use((config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

export default function Dashboard() {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [authLoading, setAuthLoading] = useState(true);

    // Check authentication status
    useEffect(() => {
        const token = localStorage.getItem('auth_token');
        if (token) {
            setIsAuthenticated(true);
        }
        setAuthLoading(false);
    }, []);

    // Fetch real system status
    const { data: systemStatus, error: systemError, isLoading: systemLoading } = useQuery({
        queryKey: ['system-status'],
        queryFn: async () => {
            const response = await axios.get('/api/system/status');
            if (!response.data.success) {
                throw new Error('Failed to fetch system status');
            }
            return response.data.data;
        },
        refetchInterval: 5000,
        enabled: isAuthenticated, // Only fetch when authenticated
    });

    // Fetch dashboard data
    const { data: dashboardData, error: dashboardError, isLoading: dashboardLoading } = useQuery({
        queryKey: ['dashboard-data'],
        queryFn: async () => {
            const response = await axios.get('/api/dashboard');
            return response.data;
        },
        refetchInterval: 10000,
        enabled: isAuthenticated,
    });

    // Handle authentication
    const handleLogin = async (email: string, password: string) => {
        try {
            const response = await axios.post('/auth/login', { email, password });
            localStorage.setItem('auth_token', response.data.access_token);
            localStorage.setItem('user_info', JSON.stringify({
                user_id: response.data.user_id,
                email: response.data.email,
                name: response.data.name,
                role: response.data.role
            }));
            setIsAuthenticated(true);
        } catch (error) {
            console.error('Login failed:', error);
            throw error;
        }
    };

    // Show login form if not authenticated
    if (authLoading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    if (!isAuthenticated) {
        return <LoginForm onLogin={handleLogin} />;
    }

    if (systemError) {
        return (
            <div className="bg-red-50 border border-red-200 rounded-lg p-6">
                <h2 className="text-red-800 font-medium">System Connection Error</h2>
                <p className="text-red-600 text-sm mt-1">Cannot connect to trading system. Check system configuration.</p>
                <button
                    onClick={() => window.location.reload()}
                    className="mt-3 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
                >
                    Retry Connection
                </button>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <h1 className="text-3xl font-bold text-gray-900">Trading Dashboard</h1>
                <div className="flex items-center space-x-4">
                    <div className={`px-3 py-1 rounded-full text-sm font-medium ${systemStatus?.status === 'operational'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-red-100 text-red-800'
                        }`}>
                        {systemStatus?.status || 'Unknown'}
                    </div>
                    <button
                        onClick={() => {
                            localStorage.removeItem('auth_token');
                            localStorage.removeItem('user_info');
                            setIsAuthenticated(false);
                        }}
                        className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
                    >
                        Logout
                    </button>
                </div>
            </div>

            {/* System Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <div className="bg-white rounded-lg shadow p-6">
                    <h3 className="text-sm font-medium text-gray-500">System Status</h3>
                    <p className="text-2xl font-bold text-gray-900">
                        {systemLoading ? 'Loading...' : (systemStatus?.status || 'Unknown')}
                    </p>
                </div>
                <div className="bg-white rounded-lg shadow p-6">
                    <h3 className="text-sm font-medium text-gray-500">Orchestrator</h3>
                    <p className="text-2xl font-bold text-gray-900">
                        {systemStatus?.orchestrator_status || 'Unknown'}
                    </p>
                </div>
                <div className="bg-white rounded-lg shadow p-6">
                    <h3 className="text-sm font-medium text-gray-500">Environment</h3>
                    <p className="text-2xl font-bold text-gray-900">
                        {systemStatus?.environment || 'Unknown'}
                    </p>
                </div>
                <div className="bg-white rounded-lg shadow p-6">
                    <h3 className="text-sm font-medium text-gray-500">Version</h3>
                    <p className="text-2xl font-bold text-gray-900">
                        {systemStatus?.version || 'Unknown'}
                    </p>
                </div>
            </div>

            {/* Dashboard Metrics */}
            {dashboardData && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    <div className="bg-white rounded-lg shadow p-6">
                        <h3 className="text-sm font-medium text-gray-500">Portfolio Value</h3>
                        <p className="text-2xl font-bold text-gray-900">
                            ₹{dashboardData.metrics?.portfolio_value?.toLocaleString() || '0'}
                        </p>
                    </div>
                    <div className="bg-white rounded-lg shadow p-6">
                        <h3 className="text-sm font-medium text-gray-500">Today's P&L</h3>
                        <p className={`text-2xl font-bold ${(dashboardData.metrics?.todays_pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                            }`}>
                            ₹{dashboardData.metrics?.todays_pnl?.toLocaleString() || '0'}
                        </p>
                    </div>
                    <div className="bg-white rounded-lg shadow p-6">
                        <h3 className="text-sm font-medium text-gray-500">Active Positions</h3>
                        <p className="text-2xl font-bold text-gray-900">
                            {dashboardData.metrics?.active_positions || '0'}
                        </p>
                    </div>
                </div>
            )}

            {/* System Components Status */}
            <div className="bg-white rounded-lg shadow">
                <div className="px-6 py-4 border-b border-gray-200">
                    <h2 className="text-lg font-medium text-gray-900">System Components</h2>
                </div>
                <div className="p-6">
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                        {systemStatus?.components && Object.entries(systemStatus.components).map(([component, status]) => (
                            <div key={component} className="flex items-center">
                                <div className={`w-3 h-3 rounded-full mr-2 ${status ? 'bg-green-500' : 'bg-red-500'
                                    }`}></div>
                                <span className="text-sm text-gray-700 capitalize">
                                    {component.replace('_', ' ')}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}

// Simple login form component
function LoginForm({ onLogin }: { onLogin: (email: string, password: string) => Promise<void> }) {
    const [email, setEmail] = useState('demo@trade123.com');
    const [password, setPassword] = useState('demo123');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        try {
            await onLogin(email, password);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Login failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <div className="max-w-md w-full space-y-8">
                <div>
                    <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
                        Trading System Login
                    </h2>
                </div>
                <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
                    {error && (
                        <div className="bg-red-50 border border-red-200 rounded p-3">
                            <p className="text-red-800 text-sm">{error}</p>
                        </div>
                    )}
                    <div>
                        <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                            Email
                        </label>
                        <input
                            id="email"
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                            required
                        />
                    </div>
                    <div>
                        <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                            Password
                        </label>
                        <input
                            id="password"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                            required
                        />
                    </div>
                    <div>
                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                        >
                            {loading ? 'Logging in...' : 'Login'}
                        </button>
                    </div>
                    <div className="text-center text-sm text-gray-600">
                        <p>Demo credentials:</p>
                        <p>Email: demo@trade123.com | Password: demo123</p>
                        <p>Email: admin@trade123.com | Password: admin123</p>
                    </div>
                </form>
            </div>
        </div>
    );
} 