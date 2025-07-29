import { TrendingDownIcon, TrendingUpIcon } from '@heroicons/react/24/outline';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

interface IndexData {
    symbol: string;
    ltp: number;
    change: number;
    change_percent: number;
    volume: number;
}

interface MarketStatus {
    is_open: boolean;
    market_type: string;
    session: string;
    open_time: string;
    close_time: string;
}

export default function LiveIndices() {
    // REAL MARKET INDICES - NO FALLBACK DATA ALLOWED
    const { data: indices, isLoading: indicesLoading, error: indicesError } = useQuery<IndexData[]>({
        queryKey: ['market-indices'],
        queryFn: async () => {
            // ONLY REAL DATA - NO FALLBACK/MOCK DATA
            const response = await axios.get('/api/market/indices');
            if (!response.data.success || response.data.source !== 'sharekhan_live') {
                throw new Error('SAFETY: Only real ShareKhan data allowed - no fallback data');
            }
            return response.data.data;
        },
        refetchInterval: 5000, // Update every 5 seconds
        retry: false, // NO RETRY WITH MOCK DATA
    });

    // REAL MARKET STATUS - NO FALLBACK DATA ALLOWED  
    const { data: marketStatus, isLoading: statusLoading, error: statusError } = useQuery<MarketStatus>({
        queryKey: ['market-status'],
        queryFn: async () => {
            // ONLY REAL DATA - NO FALLBACK/MOCK DATA
            const response = await axios.get('/api/market/market-status');
            if (!response.data.success || response.data.source !== 'sharekhan_live') {
                throw new Error('SAFETY: Only real ShareKhan data allowed - no fallback data');
            }
            return response.data.data;
        },
        refetchInterval: 30000, // Update every 30 seconds
        retry: false, // NO RETRY WITH MOCK DATA
    });

    if (indicesLoading || statusLoading) {
        return (
            <div className="p-6">
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                    <p className="text-blue-800 font-medium">🔄 Loading REAL market data from ShareKhan...</p>
                    <p className="text-blue-600 text-sm mt-1">No fallback data - waiting for live connection</p>
                </div>
            </div>
        );
    }

    if (indicesError || statusError) {
        return (
            <div className="p-6">
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
                    <h3 className="text-red-800 font-medium">❌ REAL DATA CONNECTION ERROR</h3>
                    <p className="text-red-700 text-sm mt-1">
                        ShareKhan connection unavailable. No fallback data allowed.
                    </p>
                    <p className="text-red-600 text-xs mt-2">
                        Error: {indicesError?.message || statusError?.message}
                    </p>
                    <div className="mt-3">
                        <button
                            onClick={() => window.location.reload()}
                            className="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700"
                        >
                            Retry Real Connection
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="p-6">
            {/* REAL MARKET STATUS */}
            <div className="bg-white rounded-lg shadow-md p-6 mb-6">
                <div className="flex items-center justify-between">
                    <h2 className="text-2xl font-bold text-gray-900">Live Market Indices</h2>
                    <div className="flex items-center space-x-4">
                        <div className={`px-3 py-1 rounded-full text-sm font-medium ${marketStatus?.is_open
                                ? 'bg-green-100 text-green-800'
                                : 'bg-red-100 text-red-800'
                            }`}>
                            {marketStatus?.is_open ? '🟢 MARKET OPEN' : '🔴 MARKET CLOSED'}
                        </div>
                        <div className="text-sm text-gray-600">
                            Session: {marketStatus?.session || 'Unknown'}
                        </div>
                        <div className="text-xs text-green-600 font-medium">
                            📡 LIVE SHAREKHAN DATA
                        </div>
                    </div>
                </div>
            </div>

            {/* REAL INDICES GRID */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {indices?.map((index) => (
                    <div key={index.symbol} className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-semibold text-gray-900">{index.symbol}</h3>
                            <div className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                                LIVE
                            </div>
                        </div>

                        <div className="mb-4">
                            <div className="text-2xl font-bold text-gray-900">
                                ₹{index.ltp.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                            </div>
                        </div>

                        <div className="flex items-center justify-between">
                            <div className={`flex items-center space-x-1 ${index.change >= 0 ? 'text-green-600' : 'text-red-600'
                                }`}>
                                {index.change >= 0 ? (
                                    <TrendingUpIcon className="h-4 w-4" />
                                ) : (
                                    <TrendingDownIcon className="h-4 w-4" />
                                )}
                                <span className="font-medium">
                                    {index.change >= 0 ? '+' : ''}{index.change.toFixed(2)}
                                </span>
                                <span className="text-sm">
                                    ({index.change_percent >= 0 ? '+' : ''}{index.change_percent.toFixed(2)}%)
                                </span>
                            </div>
                            <div className="text-sm text-gray-500">
                                Vol: {index.volume.toLocaleString('en-IN')}
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* REAL DATA SOURCE INDICATOR */}
            <div className="mt-6 bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                        <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                        <span className="text-green-800 font-medium">Live ShareKhan Data Stream</span>
                    </div>
                    <div className="text-green-600 text-sm">
                        Last Updated: {new Date().toLocaleTimeString('en-IN')}
                    </div>
                </div>
                <p className="text-green-700 text-sm mt-2">
                    ✅ 100% Real Production Data - No Mock/Demo/Simulation Data
                </p>
            </div>
        </div>
    );
} 