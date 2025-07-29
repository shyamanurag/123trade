import { ArrowTrendingUpIcon, TrendingDownIcon } from '@heroicons/react/24/outline';
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
    // Market Indices Query - ONLY REAL DATA
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

    // Market Status Query - ONLY REAL DATA
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
                <h1 className="text-2xl font-bold text-gray-900 mb-6">Live Market Indices</h1>
                <div className="animate-pulse">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {[1, 2, 3, 4, 5, 6].map((i) => (
                            <div key={i} className="bg-gray-200 rounded-lg h-32"></div>
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    if (indicesError || statusError) {
        return (
            <div className="p-6">
                <h1 className="text-2xl font-bold text-gray-900 mb-6">Live Market Indices</h1>
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <div className="flex">
                        <div className="flex-shrink-0">
                            <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                            </svg>
                        </div>
                        <div className="ml-3">
                            <h3 className="text-sm font-medium text-red-800">
                                Real Data Connection Error
                            </h3>
                            <div className="mt-2 text-sm text-red-700">
                                <p>Unable to fetch real market data from ShareKhan API.</p>
                                <p className="mt-1">Error: {(indicesError as Error)?.message || (statusError as Error)?.message}</p>
                                <p className="mt-2 font-medium">NO FALLBACK DATA ALLOWED - System requires live ShareKhan connection.</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="p-6">
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl font-bold text-gray-900">Live Market Indices</h1>
                <div className="flex items-center space-x-2">
                    <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${marketStatus?.is_open
                            ? 'bg-green-100 text-green-800'
                            : 'bg-red-100 text-red-800'
                        }`}>
                        {marketStatus?.is_open ? 'Market Open' : 'Market Closed'}
                    </div>
                    <div className="text-xs text-gray-500">
                        Last updated: {new Date().toLocaleTimeString()}
                    </div>
                    <div className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800">
                        📊 REAL SHAREKHAN DATA
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {indices?.map((index, i) => (
                    <div
                        key={index.symbol}
                        className="bg-white overflow-hidden shadow rounded-lg border border-gray-200 hover:shadow-md transition-shadow"
                    >
                        <div className="p-5">
                            <div className="flex items-center">
                                <div className="flex-shrink-0">
                                    <div className="flex items-center justify-center h-8 w-8 bg-blue-500 text-white rounded-md text-sm font-medium">
                                        {index.symbol.slice(0, 2)}
                                    </div>
                                </div>
                                <div className="ml-5 w-0 flex-1">
                                    <dl>
                                        <dt className="text-sm font-medium text-gray-500 truncate">
                                            {index.symbol}
                                        </dt>
                                        <dd className="text-lg font-medium text-gray-900">
                                            ₹{index.ltp?.toLocaleString() || 'N/A'}
                                        </dd>
                                    </dl>
                                </div>
                            </div>

                            <div className="flex items-center justify-between">
                                <div className={`flex items-center space-x-1 ${index.change >= 0 ? 'text-green-600' : 'text-red-600'
                                    }`}>
                                    {index.change >= 0 ? (
                                        <ArrowTrendingUpIcon className="h-4 w-4" />
                                    ) : (
                                        <TrendingDownIcon className="h-4 w-4" />
                                    )}
                                    <span className="font-medium">
                                        {index.change >= 0 ? '+' : ''}{index.change?.toFixed(2) || 'N/A'}
                                    </span>
                                    <span className="text-sm">
                                        ({index.change >= 0 ? '+' : ''}{index.change_percent?.toFixed(2) || 'N/A'}%)
                                    </span>
                                </div>
                                <div className="text-sm text-gray-500">
                                    Vol: {index.volume?.toLocaleString() || 'N/A'}
                                </div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {(!indices || indices.length === 0) && (
                <div className="text-center py-12">
                    <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                    <h3 className="mt-2 text-sm font-medium text-gray-900">No market data available</h3>
                    <p className="mt-1 text-sm text-gray-500">
                        Waiting for real ShareKhan market data feed...
                    </p>
                </div>
            )}
        </div>
    );
} 