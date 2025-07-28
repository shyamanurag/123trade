import { CheckCircleIcon, CircleStackIcon, ClockIcon, CpuChipIcon, ServerIcon, XCircleIcon } from '@heroicons/react/24/outline';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

interface SystemMetrics {
    cpu_usage: number;
    memory_usage: number;
    disk_usage: number;
    network_latency: number;
    active_connections: number;
    uptime_seconds: number;
}

interface DatabaseHealth {
    status: 'healthy' | 'degraded' | 'down';
    response_time_ms: number;
    active_connections: number;
    total_queries_today: number;
    error_rate: number;
}

interface ApiHealth {
    sharekhan_api: {
        status: 'connected' | 'disconnected' | 'error';
        last_response_time: number;
        success_rate: number;
    };
    market_data_feed: {
        status: 'connected' | 'disconnected' | 'error';
        last_update: string;
        symbols_tracked: number;
    };
    redis_cache: {
        status: 'healthy' | 'degraded' | 'down';
        hit_rate: number;
        memory_usage: number;
    };
}

interface SystemLogs {
    timestamp: string;
    level: 'info' | 'warning' | 'error';
    message: string;
    component: string;
}

export default function SystemHealth() {
    // Fetch system metrics
    const { data: systemMetrics } = useQuery<SystemMetrics>({
        queryKey: ['system-metrics'],
        queryFn: async () => {
            const response = await axios.get('/api/system/metrics');
            if (!response.data.success) {
                throw new Error('Failed to fetch system metrics');
            }
            return response.data.data;
        },
        refetchInterval: 5000,
    });

    // Fetch database health
    const { data: databaseHealth } = useQuery<DatabaseHealth>({
        queryKey: ['database-health'],
        queryFn: async () => {
            const response = await axios.get('/api/system/database-health');
            if (!response.data.success) {
                throw new Error('Failed to fetch database health');
            }
            return response.data.data;
        },
        refetchInterval: 10000,
    });

    // Fetch API health
    const { data: apiHealth } = useQuery<ApiHealth>({
        queryKey: ['api-health'],
        queryFn: async () => {
            const response = await axios.get('/api/system/api-health');
            if (!response.data.success) {
                throw new Error('Failed to fetch API health');
            }
            return response.data.data;
        },
        refetchInterval: 15000,
    });

    // Fetch system logs
    const { data: systemLogs } = useQuery<SystemLogs[]>({
        queryKey: ['system-logs'],
        queryFn: async () => {
            const response = await axios.get('/api/system/logs', {
                params: { limit: 50 }
            });
            if (!response.data.success) {
                throw new Error('Failed to fetch system logs');
            }
            return response.data.data;
        },
        refetchInterval: 30000,
    });

    const formatUptime = (seconds: number) => {
        const days = Math.floor(seconds / (24 * 3600));
        const hours = Math.floor((seconds % (24 * 3600)) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${days}d ${hours}h ${minutes}m`;
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'healthy':
            case 'connected':
                return 'text-green-600';
            case 'degraded':
            case 'warning':
                return 'text-yellow-600';
            case 'down':
            case 'disconnected':
            case 'error':
                return 'text-red-600';
            default:
                return 'text-gray-600';
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'healthy':
            case 'connected':
                return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
            case 'degraded':
            case 'warning':
                return <ClockIcon className="h-5 w-5 text-yellow-500" />;
            case 'down':
            case 'disconnected':
            case 'error':
                return <XCircleIcon className="h-5 w-5 text-red-500" />;
            default:
                return <ClockIcon className="h-5 w-5 text-gray-500" />;
        }
    };

    const getLogLevelColor = (level: string) => {
        switch (level) {
            case 'info': return 'text-blue-600 bg-blue-50';
            case 'warning': return 'text-yellow-600 bg-yellow-50';
            case 'error': return 'text-red-600 bg-red-50';
            default: return 'text-gray-600 bg-gray-50';
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">System Health Monitor</h1>
                    <p className="mt-1 text-sm text-gray-600">
                        Real-time ShareKhan trading system monitoring and diagnostics
                    </p>
                </div>
            </div>

            {/* System Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <div className="bg-white rounded-lg shadow p-6">
                    <div className="flex items-center">
                        <CpuChipIcon className="h-8 w-8 text-blue-500" />
                        <div className="ml-4">
                            <p className="text-sm font-medium text-gray-600">CPU Usage</p>
                            <p className="text-2xl font-bold text-gray-900">
                                {systemMetrics?.cpu_usage?.toFixed(1) || 0}%
                            </p>
                        </div>
                    </div>
                </div>

                <div className="bg-white rounded-lg shadow p-6">
                    <div className="flex items-center">
                        <ServerIcon className="h-8 w-8 text-green-500" />
                        <div className="ml-4">
                            <p className="text-sm font-medium text-gray-600">Memory Usage</p>
                            <p className="text-2xl font-bold text-gray-900">
                                {systemMetrics?.memory_usage?.toFixed(1) || 0}%
                            </p>
                        </div>
                    </div>
                </div>

                <div className="bg-white rounded-lg shadow p-6">
                    <div className="flex items-center">
                        <CircleStackIcon className="h-8 w-8 text-purple-500" />
                        <div className="ml-4">
                            <p className="text-sm font-medium text-gray-600">Disk Usage</p>
                            <p className="text-2xl font-bold text-gray-900">
                                {systemMetrics?.disk_usage?.toFixed(1) || 0}%
                            </p>
                        </div>
                    </div>
                </div>

                <div className="bg-white rounded-lg shadow p-6">
                    <div className="flex items-center">
                        <ClockIcon className="h-8 w-8 text-orange-500" />
                        <div className="ml-4">
                            <p className="text-sm font-medium text-gray-600">Uptime</p>
                            <p className="text-lg font-bold text-gray-900">
                                {systemMetrics?.uptime_seconds ? formatUptime(systemMetrics.uptime_seconds) : '0d 0h 0m'}
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Database Health */}
            <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-medium text-gray-900 mb-4">Database Health</h2>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div className="text-center p-4 bg-gray-50 rounded-lg">
                        <div className="flex items-center justify-center mb-2">
                            {getStatusIcon(databaseHealth?.status || 'unknown')}
                        </div>
                        <div className={`font-semibold capitalize ${getStatusColor(databaseHealth?.status || 'unknown')}`}>
                            {databaseHealth?.status || 'Unknown'}
                        </div>
                    </div>
                    <div className="text-center p-4 bg-gray-50 rounded-lg">
                        <div className="text-2xl font-bold text-blue-600">
                            {databaseHealth?.response_time_ms || 0}ms
                        </div>
                        <div className="text-sm text-gray-600">Response Time</div>
                    </div>
                    <div className="text-center p-4 bg-gray-50 rounded-lg">
                        <div className="text-2xl font-bold text-purple-600">
                            {databaseHealth?.active_connections || 0}
                        </div>
                        <div className="text-sm text-gray-600">Active Connections</div>
                    </div>
                    <div className="text-center p-4 bg-gray-50 rounded-lg">
                        <div className="text-2xl font-bold text-green-600">
                            {databaseHealth?.total_queries_today || 0}
                        </div>
                        <div className="text-sm text-gray-600">Queries Today</div>
                    </div>
                </div>
            </div>

            {/* API Health */}
            <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-medium text-gray-900 mb-4">External API Health</h2>
                <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                        <div className="flex items-center">
                            {getStatusIcon(apiHealth?.sharekhan_api?.status || 'unknown')}
                            <span className="ml-3 font-medium">ShareKhan API</span>
                        </div>
                        <div className="text-right">
                            <div className="text-sm text-gray-600">Response Time: {apiHealth?.sharekhan_api?.last_response_time || 0}ms</div>
                            <div className="text-sm text-gray-600">Success Rate: {apiHealth?.sharekhan_api?.success_rate || 0}%</div>
                        </div>
                    </div>

                    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                        <div className="flex items-center">
                            {getStatusIcon(apiHealth?.market_data_feed?.status || 'unknown')}
                            <span className="ml-3 font-medium">Market Data Feed</span>
                        </div>
                        <div className="text-right">
                            <div className="text-sm text-gray-600">Symbols: {apiHealth?.market_data_feed?.symbols_tracked || 0}</div>
                            <div className="text-sm text-gray-600">
                                Last Update: {apiHealth?.market_data_feed?.last_update ?
                                    new Date(apiHealth.market_data_feed.last_update).toLocaleTimeString() : 'Never'}
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                        <div className="flex items-center">
                            {getStatusIcon(apiHealth?.redis_cache?.status || 'unknown')}
                            <span className="ml-3 font-medium">Redis Cache</span>
                        </div>
                        <div className="text-right">
                            <div className="text-sm text-gray-600">Hit Rate: {apiHealth?.redis_cache?.hit_rate || 0}%</div>
                            <div className="text-sm text-gray-600">Memory: {apiHealth?.redis_cache?.memory_usage || 0}MB</div>
                        </div>
                    </div>
                </div>
            </div>

            {/* System Logs */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200">
                    <h2 className="text-lg font-medium text-gray-900">Recent System Logs</h2>
                </div>
                <div className="max-h-96 overflow-y-auto">
                    {systemLogs && systemLogs.length > 0 ? (
                        <div className="divide-y divide-gray-200">
                            {systemLogs.map((log, index) => (
                                <div key={index} className="p-4 hover:bg-gray-50">
                                    <div className="flex items-start justify-between">
                                        <div className="flex-1">
                                            <div className="flex items-center space-x-2">
                                                <span className={`px-2 py-1 text-xs font-medium rounded ${getLogLevelColor(log.level)}`}>
                                                    {log.level.toUpperCase()}
                                                </span>
                                                <span className="text-sm text-gray-600">{log.component}</span>
                                            </div>
                                            <p className="mt-1 text-sm text-gray-900">{log.message}</p>
                                        </div>
                                        <div className="text-xs text-gray-500">
                                            {new Date(log.timestamp).toLocaleString()}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="p-6 text-center text-gray-500">
                            No recent logs available
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
} 