import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

export default function Dashboard() {
    // Fetch real system status
    const { data: systemStatus, error: systemError } = useQuery({
        queryKey: ['system-status'],
        queryFn: async () => {
            const response = await axios.get('/api/system/status');
            if (!response.data.success) {
                throw new Error('Failed to fetch system status');
            }
            return response.data.data;
        },
        refetchInterval: 5000,
    });

    if (systemError) {
        return (
            <div className="bg-red-50 border border-red-200 rounded-lg p-6">
                <h2 className="text-red-800 font-medium">System Connection Error</h2>
                <p className="text-red-600 text-sm mt-1">Cannot connect to trading system. Check system configuration.</p>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-gray-900">ShareKhan Trading System Dashboard</h1>
                <p className="mt-1 text-sm text-gray-600">
                    Live trading system overview - Real data only
                </p>
            </div>

            {systemStatus ? (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="bg-white rounded-lg shadow p-6">
                        <h3 className="text-lg font-medium text-gray-900 mb-2">System Status</h3>
                        <p className={`text-2xl font-bold ${systemStatus.orchestrator_health === 'healthy' ? 'text-green-600' : 'text-red-600'
                            }`}>
                            {systemStatus.orchestrator_health || 'Unknown'}
                        </p>
                    </div>

                    <div className="bg-white rounded-lg shadow p-6">
                        <h3 className="text-lg font-medium text-gray-900 mb-2">Active Users</h3>
                        <p className="text-2xl font-bold text-blue-600">
                            {systemStatus.active_users || 0}
                        </p>
                    </div>

                    <div className="bg-white rounded-lg shadow p-6">
                        <h3 className="text-lg font-medium text-gray-900 mb-2">Today's Trades</h3>
                        <p className="text-2xl font-bold text-purple-600">
                            {systemStatus.total_trades_today || 0}
                        </p>
                    </div>
                </div>
            ) : (
                <div className="bg-white rounded-lg shadow p-6 text-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                    <p className="mt-2 text-gray-600">Loading real system data...</p>
                </div>
            )}

            <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-medium text-gray-900 mb-4">Quick Actions</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <a
                        href="/auth-tokens"
                        className="block p-4 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
                    >
                        <h3 className="font-medium text-blue-900">Daily Auth Tokens</h3>
                        <p className="text-sm text-blue-700 mt-1">Manage ShareKhan authentication</p>
                    </a>

                    <a
                        href="/analytics"
                        className="block p-4 bg-green-50 rounded-lg hover:bg-green-100 transition-colors"
                    >
                        <h3 className="font-medium text-green-900">User Analytics</h3>
                        <p className="text-sm text-green-700 mt-1">View real P&L and positions</p>
                    </a>

                    <a
                        href="/indices"
                        className="block p-4 bg-purple-50 rounded-lg hover:bg-purple-100 transition-colors"
                    >
                        <h3 className="font-medium text-purple-900">Live Indices</h3>
                        <p className="text-sm text-purple-700 mt-1">Real-time market data</p>
                    </a>

                    <a
                        href="/system"
                        className="block p-4 bg-orange-50 rounded-lg hover:bg-orange-100 transition-colors"
                    >
                        <h3 className="font-medium text-orange-900">System Health</h3>
                        <p className="text-sm text-orange-700 mt-1">Monitor system status</p>
                    </a>
                </div>
            </div>
        </div>
    );
} 