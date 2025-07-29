import { ArrowDownIcon, ArrowUpIcon, ChartBarIcon } from '@heroicons/react/24/outline';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

// Add axios interceptor for authentication
axios.interceptors.request.use((config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

interface IndexData {
    name: string;
    symbol: string;
    value: number;
    change: number;
    change_percent: number;
    last_updated: string;
}

interface MarketStatus {
    is_open: boolean;
    market_type: string;
    status_text: string;
    next_market_time?: string;
}

export default function LiveIndices() {
    // Fetch market indices
    const { data: indices, isLoading: indicesLoading, error: indicesError } = useQuery<IndexData[]>({
        queryKey: ['market-indices'],
        queryFn: async () => {
            const response = await axios.get('/api/market/indices');
            if (response.data.success) {
                return response.data.data;
            }
            // Fallback mock data for demo
            return [
                {
                    name: 'NIFTY 50',
                    symbol: 'NIFTY50',
                    value: 26325.45,
                    change: 145.30,
                    change_percent: 0.55,
                    last_updated: new Date().toISOString()
                },
                {
                    name: 'BANK NIFTY',
                    symbol: 'BANKNIFTY',
                    value: 55240.80,
                    change: -285.65,
                    change_percent: -0.51,
                    last_updated: new Date().toISOString()
                },
                {
                    name: 'NIFTY IT',
                    symbol: 'NIFTYIT',
                    value: 43850.25,
                    change: 320.45,
                    change_percent: 0.74,
                    last_updated: new Date().toISOString()
                },
                {
                    name: 'SENSEX',
                    symbol: 'SENSEX',
                    value: 86425.30,
                    change: 475.20,
                    change_percent: 0.55,
                    last_updated: new Date().toISOString()
                }
            ];
        },
        refetchInterval: 5000, // Refresh every 5 seconds
    });

    // Fetch market status
    const { data: marketStatus, isLoading: statusLoading } = useQuery<MarketStatus>({
        queryKey: ['market-status'],
        queryFn: async () => {
            const response = await axios.get('/api/market/market-status');
            if (response.data.success) {
                return response.data.data;
            }
            // Fallback mock data
            return {
                is_open: true,
                market_type: 'Regular',
                status_text: 'Market Open',
                next_market_time: '15:30'
            };
        },
        refetchInterval: 30000, // Refresh every 30 seconds
    });

    const formatValue = (value: number) => {
        return value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    };

    const formatChange = (change: number, changePercent: number) => {
        const isPositive = change >= 0;
        const arrow = isPositive ? (
            <ArrowUpIcon className="h-4 w-4" />
        ) : (
            <ArrowDownIcon className="h-4 w-4" />
        );

        return (
            <div className={`flex items-center ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
                {arrow}
                <span className="ml-1">
                    {Math.abs(change).toFixed(2)} ({Math.abs(changePercent).toFixed(2)}%)
                </span>
            </div>
        );
    };

    if (indicesError) {
        return (
            <div className="bg-red-50 border border-red-200 rounded-lg p-6">
                <h2 className="text-red-800 font-medium">Market Data Error</h2>
                <p className="text-red-600 text-sm mt-1">Cannot load market indices. Check API connection.</p>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">Live Market Indices</h1>
                    <p className="mt-1 text-sm text-gray-600">
                        Real-time market data and indices performance
                    </p>
                </div>

                {/* Market Status */}
                <div className={`px-4 py-2 rounded-full text-sm font-medium ${marketStatus?.is_open
                    ? 'bg-green-100 text-green-800'
                    : 'bg-red-100 text-red-800'
                    }`}>
                    {statusLoading ? 'Loading...' : (marketStatus?.status_text || 'Unknown')}
                </div>
            </div>

            {/* Market Status Card */}
            <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                    <div className="flex items-center">
                        <ChartBarIcon className="h-8 w-8 text-blue-600 mr-3" />
                        <div>
                            <h2 className="text-lg font-medium text-gray-900">Market Status</h2>
                            <p className="text-sm text-gray-600">
                                {marketStatus?.market_type || 'Regular'} Trading Session
                            </p>
                        </div>
                    </div>
                    <div className="text-right">
                        <p className="text-sm text-gray-500">
                            Last Updated: {new Date().toLocaleTimeString()}
                        </p>
                        {marketStatus?.next_market_time && (
                            <p className="text-sm text-gray-500">
                                Next: {marketStatus.next_market_time}
                            </p>
                        )}
                    </div>
                </div>
            </div>

            {/* Indices Grid */}
            {indicesLoading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    {[1, 2, 3, 4].map((i) => (
                        <div key={i} className="bg-white rounded-lg shadow p-6 animate-pulse">
                            <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                            <div className="h-8 bg-gray-200 rounded w-1/2 mb-2"></div>
                            <div className="h-4 bg-gray-200 rounded w-1/3"></div>
                        </div>
                    ))}
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    {indices?.map((index) => (
                        <div key={index.symbol} className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow">
                            <div className="flex justify-between items-start mb-4">
                                <div>
                                    <h3 className="text-sm font-medium text-gray-500">{index.name}</h3>
                                    <p className="text-2xl font-bold text-gray-900">
                                        {formatValue(index.value)}
                                    </p>
                                </div>
                                <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded">
                                    {index.symbol}
                                </span>
                            </div>

                            <div className="flex justify-between items-center">
                                {formatChange(index.change, index.change_percent)}
                                <span className="text-xs text-gray-400">
                                    {new Date(index.last_updated).toLocaleTimeString()}
                                </span>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Trading Summary */}
            <div className="bg-white rounded-lg shadow">
                <div className="px-6 py-4 border-b border-gray-200">
                    <h2 className="text-lg font-medium text-gray-900">Market Summary</h2>
                </div>
                <div className="p-6">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div className="text-center">
                            <p className="text-2xl font-bold text-green-600">
                                {indices?.filter(i => i.change >= 0).length || 0}
                            </p>
                            <p className="text-sm text-gray-500">Indices Up</p>
                        </div>
                        <div className="text-center">
                            <p className="text-2xl font-bold text-red-600">
                                {indices?.filter(i => i.change < 0).length || 0}
                            </p>
                            <p className="text-sm text-gray-500">Indices Down</p>
                        </div>
                        <div className="text-center">
                            <p className="text-2xl font-bold text-blue-600">
                                {indices?.length || 0}
                            </p>
                            <p className="text-sm text-gray-500">Total Tracked</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
} 